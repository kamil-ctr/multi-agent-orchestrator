"""Wires together Stages 1-5 into a single pipeline run, with caching and
history persistence bolted on around it. This is the one object the UI
layer talks to.
"""
from __future__ import annotations

from collections.abc import Callable

from agents.base import BaseAgent
from agents.registry import build_agents
from core.cache import ResponseCache
from core.config import AppConfig
from core.cost_tracker import estimate_cost_usd, estimate_tokens
from core.cost_tracker import total_tokens as sum_tokens
from core.history import HistoryStore
from core.logger import get_logger
from core.schemas import AgentResponse, AgentStatus, ImageInput, PipelineResult
from pipeline.dispatch import dispatch_streaming, dispatch_streaming_mm, dispatch_streaming_tokens
from pipeline.evaluate import compute_confidence, heuristic_score, llm_judge_refine, rank, score_all_heuristic
from pipeline.normalize import normalize_responses, summarize
from pipeline.preprocess import classify_query_type, expand_query, preprocess
from pipeline.synthesize import synthesize

logger = get_logger(__name__)


class Orchestrator:
    """Composition root for the pipeline: builds the agent roster once and
    exposes two entrypoints — `run()` for the CLI's simple case and
    `run_streaming()` for the web API's SSE-driven case — plus cache and
    history persistence shared by both."""

    def __init__(self, config: AppConfig) -> None:
        """Build the agent roster from config and open the cache/history stores.

        Args:
            config: The loaded AppConfig (see core.config.load_config) —
                determines which agents are instantiated, the judge agent,
                cache TTL, and where the SQLite stores live on disk.
        """
        self.config = config
        self.agents: list[BaseAgent] = build_agents(config)
        self.agents_by_name: dict[str, BaseAgent] = {a.name: a for a in self.agents}
        self.cache = ResponseCache(config.data_dir / "cache.sqlite", config.cache_ttl_seconds)
        self.history = HistoryStore(config.data_dir / "history.sqlite")

    def judge_agent(self) -> BaseAgent | None:
        """Return the configured judge/synthesizer agent, if it's in the roster.

        Returns:
            The BaseAgent named by `config.judge_agent`, or None if that
            name isn't among the currently built agents (e.g. removed from
            config.yaml) — callers must handle None as "no judge available."
        """
        return self.agents_by_name.get(self.config.judge_agent)

    def availability(self) -> dict[str, bool]:
        """Return a name -> is_available map for every configured agent.

        Used by the API's health check and the frontend's Settings page to
        show which agents have a working key without exposing the key itself.
        """
        return {a.name: a.is_available for a in self.agents}

    async def run(
        self,
        prompt: str,
        use_cache: bool = True,
        record_history: bool = True,
        on_agent_result: Callable[[AgentResponse], None] | None = None,
    ) -> PipelineResult:
        """Run the full 5-stage pipeline for one prompt (CLI entrypoint).

        Text-only entrypoint used by the Rich CLI — for image/file
        attachments and SSE-style lifecycle events, use `run_streaming`
        instead (the two share every pipeline stage underneath).

        Args:
            prompt: The user's prompt.
            use_cache: Whether to check/populate the prompt-hash cache.
            record_history: Whether to persist this run to the history store.
            on_agent_result: Optional callback invoked with each
                AgentResponse as it completes, for live CLI progress display.

        Returns:
            The full PipelineResult, including per-agent responses,
            evaluations, the synthesized answer, and confidence score.

        Raises:
            ValueError: If prompt is empty or whitespace-only.
        """
        if not prompt or not prompt.strip():
            raise ValueError("prompt must not be empty")

        if use_cache:
            cached = self.cache.get(prompt)
            if cached:
                logger.info("Cache hit for prompt")
                return cached

        judge = self.judge_agent()
        pre = await preprocess(prompt, expander=judge)
        working_query = pre.expanded_prompt

        responses: list[AgentResponse] = []
        async for result in dispatch_streaming(self.agents, working_query, on_result=on_agent_result):
            responses.append(result)
        responses = normalize_responses(responses)
        summary = summarize(responses)

        heuristic_scores = score_all_heuristic(working_query, responses)
        evaluations, evaluator_used = await llm_judge_refine(working_query, responses, heuristic_scores, judge)
        evaluations = rank(evaluations)

        synthesized_answer, attribution = await synthesize(
            working_query, responses, evaluations, judge, self.config.top_n_for_synthesis
        )

        confidence = compute_confidence(evaluations, summary)

        input_tokens = estimate_tokens(working_query)
        estimated_cost = sum(
            estimate_cost_usd(self.config.agents.get(r.agent), input_tokens, r.token_count_estimate or 0)
            for r in responses
            if r.status == AgentStatus.SUCCESS
        )

        result = PipelineResult(
            query=prompt,
            query_type=pre.query_type.value,
            expanded_query=working_query if pre.was_expanded else prompt,
            agent_responses=responses,
            evaluations=evaluations,
            synthesized_answer=synthesized_answer,
            attribution=attribution,
            confidence_score=confidence,
            total_latency_ms=summary.total_latency_ms,
            total_tokens_estimate=sum_tokens(responses),
            estimated_cost_usd=round(estimated_cost, 6),
            evaluator_used=evaluator_used,
        )

        if use_cache:
            self.cache.set(prompt, result)
        if record_history:
            self.history.record(result)
        return result

    async def _describe_image(self, image: ImageInput) -> str | None:
        """Ask the first available vision-capable agent to describe an image in text.

        Used to give non-vision agents something to work with: their prompt
        gets this description substituted in, so they can still participate
        meaningfully instead of being skipped entirely on image queries.

        Args:
            image: The attached image to describe.

        Returns:
            The description text, or None if no vision-capable agent is
            available or every attempt failed.
        """
        preferred = self.agents_by_name.get("gemini")
        ordered = ([preferred] if preferred else []) + [a for a in self.agents if a.supports_vision]
        tried: set[str] = set()
        for agent in ordered:
            if agent is None or agent.name in tried or not agent.is_available:
                continue
            tried.add(agent.name)
            resp = await agent.generate(
                "Describe this image factually and in detail, for someone who cannot see it.",
                image=image,
            )
            if resp.status == AgentStatus.SUCCESS and resp.response_text:
                return resp.response_text
        return None

    async def run_streaming(
        self,
        prompt: str,
        image: ImageInput | None = None,
        file_context: str | None = None,
        use_cache: bool = True,
        record_history: bool = True,
        enabled_agents: list[str] | None = None,
        on_event: Callable[[dict], None] | None = None,
    ) -> PipelineResult:
        """Run the full pipeline with multimodal support and live lifecycle events (API entrypoint).

        Web-facing counterpart to `run()`: supports image/file attachments
        and emits structured lifecycle events (agent_start/agent_done/
        agent_error/synthesis_done) suitable for relaying over SSE.

        Args:
            prompt: The user's prompt.
            image: An optional attached image. Routed directly to
                vision-capable agents; a text description is generated (via
                `_describe_image`) and substituted in for everyone else.
            file_context: Optional extracted text from an attached document,
                prepended to the prompt as context for every agent.
            use_cache: Whether to check/populate the prompt-hash cache.
                Automatically disabled whenever image or file_context is
                present, since the cache key is prompt-text-only.
            record_history: Whether to persist this run to the history store.
            enabled_agents: When given, restricts dispatch to this subset of
                configured agent names (from the Settings page's on/off
                toggles) — None means "use every configured agent," matching
                the CLI's default.
            on_event: Optional callback invoked with a dict for each
                lifecycle event (`agent_start`, `agent_done`, `agent_error`,
                `synthesis_done`) — the API layer uses this to push events
                onto the SSE stream as they happen.

        Returns:
            The full PipelineResult, including per-agent responses,
            evaluations, the synthesized answer, and confidence score.

        Raises:
            ValueError: If prompt is empty/whitespace-only, or if
                enabled_agents filters the roster down to zero agents.
        """
        if not prompt or not prompt.strip():
            raise ValueError("prompt must not be empty")

        agents = self.agents if enabled_agents is None else [a for a in self.agents if a.name in enabled_agents]
        if not agents:
            raise ValueError("no agents selected")

        # Cache is keyed on prompt text only, so any attachment bypasses it —
        # otherwise a second image under the same caption would return stale results.
        effective_use_cache = use_cache and image is None and not file_context
        if effective_use_cache:
            cached = self.cache.get(prompt)
            if cached:
                logger.info("Cache hit for prompt")
                if on_event:
                    on_event({"type": "synthesis_done", "result": cached.to_dict(), "history_id": None})
                return cached

        working_query = prompt
        if file_context:
            working_query = f"Attached file content:\n{file_context}\n\n---\n\nUser question: {prompt}"

        query_type = classify_query_type(prompt)
        judge = self.judge_agent()

        image_description: str | None = None
        if image:
            image_description = await self._describe_image(image)
            expanded_query, was_expanded = working_query, False
        else:
            expanded_query, was_expanded = await expand_query(working_query, judge)

        if image:
            if image_description:
                text_variant = f"{expanded_query}\n\n[Attached image — description: {image_description}]"
            else:
                text_variant = (
                    f"{expanded_query}\n\n[An image was attached but no vision-capable agent "
                    "was available to describe it]"
                )
        else:
            text_variant = expanded_query

        def prompt_selector(agent: BaseAgent) -> tuple[str, ImageInput | None]:
            if image and agent.supports_vision:
                return expanded_query, image
            return text_variant, None

        if on_event:
            for agent in agents:
                on_event({"type": "agent_start", "agent": agent.name})

        responses: list[AgentResponse] = []

        def handle_result(resp: AgentResponse) -> None:
            responses.append(resp)
            if on_event is None:
                return
            if resp.status == AgentStatus.SUCCESS:
                provisional = heuristic_score(text_variant, resp, responses)
                on_event(
                    {
                        "type": "agent_done",
                        "agent": resp.agent,
                        "status": resp.status.value,
                        "latency_ms": resp.latency_ms,
                        "score": provisional.overall,
                        "model": resp.model,
                    }
                )
            else:
                on_event(
                    {
                        "type": "agent_error",
                        "agent": resp.agent,
                        "status": resp.status.value,
                        "error": resp.error,
                        "latency_ms": resp.latency_ms,
                    }
                )

        def handle_token(agent_name: str, token: str) -> None:
            if on_event:
                on_event({"type": "agent_token", "agent": agent_name, "token": token})

        if self.config.streaming_enabled:
            async for _ in dispatch_streaming_tokens(
                agents, prompt_selector, on_token=handle_token, on_result=handle_result
            ):
                pass
        else:
            async for _ in dispatch_streaming_mm(agents, prompt_selector, on_result=handle_result):
                pass

        responses = normalize_responses(responses)
        summary = summarize(responses)

        heuristic_scores = score_all_heuristic(text_variant, responses)
        evaluations, evaluator_used = await llm_judge_refine(text_variant, responses, heuristic_scores, judge)
        evaluations = rank(evaluations)

        synthesized_answer, attribution = await synthesize(
            text_variant, responses, evaluations, judge, self.config.top_n_for_synthesis
        )
        confidence = compute_confidence(evaluations, summary)

        input_tokens = estimate_tokens(text_variant)
        estimated_cost = sum(
            estimate_cost_usd(self.config.agents.get(r.agent), input_tokens, r.token_count_estimate or 0)
            for r in responses
            if r.status == AgentStatus.SUCCESS
        )

        result = PipelineResult(
            query=prompt,
            query_type=query_type.value,
            expanded_query=expanded_query if was_expanded else prompt,
            agent_responses=responses,
            evaluations=evaluations,
            synthesized_answer=synthesized_answer,
            attribution=attribution,
            confidence_score=confidence,
            total_latency_ms=summary.total_latency_ms,
            total_tokens_estimate=sum_tokens(responses),
            estimated_cost_usd=round(estimated_cost, 6),
            evaluator_used=evaluator_used,
        )

        if effective_use_cache:
            self.cache.set(prompt, result)
        history_id: int | None = None
        if record_history:
            history_id = self.history.record(result)

        if on_event:
            on_event({"type": "synthesis_done", "result": result.to_dict(), "history_id": history_id})

        return result
