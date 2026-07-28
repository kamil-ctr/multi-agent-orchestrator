"""Wires together Stages 1-5 into a single pipeline run, with caching and
history persistence bolted on around it. This is the one object the UI
layer talks to.
"""
from __future__ import annotations

from collections.abc import Callable

import httpx

from agents.base import BaseAgent
from agents.registry import build_agents
from core.cache import ResponseCache
from core.config import AppConfig
from core.conversations import ConversationStore
from core.cost_tracker import estimate_cost_usd, estimate_tokens
from core.cost_tracker import total_tokens as sum_tokens
from core.embeddings import embed_text
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
        self.conversations = ConversationStore(config.data_dir / "conversations.sqlite")

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

    async def _embed(self, text: str) -> list[float] | None:
        """Embed text for semantic cache comparison via Cohere (see core/embeddings.py).

        Returns None if no Cohere key is configured or the call fails —
        semantic caching then simply doesn't apply for this run.
        """
        cohere_cfg = self.config.agents.get("cohere")
        if cohere_cfg is None or not cohere_cfg.api_key:
            return None
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await embed_text(client, text, cohere_cfg.api_key)

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
        evaluations, evaluator_used, explanation = await llm_judge_refine(
            working_query, responses, heuristic_scores, judge
        )
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
            explanation=explanation,
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
        conversation_context: str | None = None,
        conversation_id: int | None = None,
        use_cache: bool = True,
        record_history: bool = True,
        enabled_agents: list[str] | None = None,
        semantic_cache_enabled: bool | None = None,
        semantic_cache_threshold: float | None = None,
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
            conversation_context: Optional prior-turns context (see
                ConversationStore.build_context), prepended alongside
                file_context for follow-up messages in a multi-turn
                conversation.
            conversation_id: The conversation this turn belongs to, if any —
                used only to scope semantic-cache lookups/writes to that
                conversation (never leaks across unrelated conversations).
                Exact prompt-hash caching remains conversation-blind and is
                skipped whenever conversation_context is present, since two
                identical questions can have different correct answers
                depending on what came before them.
            use_cache: Whether to check/populate the cache (exact and/or
                semantic). Exact matching is automatically disabled whenever
                image, file_context, or conversation_context is present.
                Semantic matching is disabled whenever image or file_context
                is present, but — unlike exact matching — remains active for
                conversation turns, scoped to conversation_id.
            record_history: Whether to persist this run to the history store.
            enabled_agents: When given, restricts dispatch to this subset of
                configured agent names (from the Settings page's on/off
                toggles) — None means "use every configured agent," matching
                the CLI's default.
            semantic_cache_enabled: Per-request override for
                config.semantic_cache_enabled (None uses the config default).
            semantic_cache_threshold: Per-request override for
                config.semantic_cache_threshold (None uses the config default).
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

        # Exact-hash matching is keyed on prompt text only and stays
        # conversation-blind, so it's skipped whenever there's an
        # attachment or prior conversation turn — a repeat prompt in a
        # different context could otherwise return a stale, context-blind
        # result. Semantic matching additionally requires an embedding
        # call, so it's skipped for attachments too, but (scoped by
        # conversation_id) remains available for conversation turns.
        effective_exact_cache = use_cache and image is None and not file_context and not conversation_context
        semantic_enabled = (
            self.config.semantic_cache_enabled if semantic_cache_enabled is None else semantic_cache_enabled
        )
        semantic_threshold = (
            self.config.semantic_cache_threshold if semantic_cache_threshold is None else semantic_cache_threshold
        )
        effective_semantic_cache = use_cache and image is None and not file_context and semantic_enabled

        cached: PipelineResult | None = None
        cache_hit = "miss"
        cache_similarity: float | None = None
        query_embedding: list[float] | None = None

        if effective_exact_cache:
            cached = self.cache.get(prompt)
            if cached:
                cache_hit = "exact"

        if cached is None and effective_semantic_cache:
            query_embedding = await self._embed(prompt)
            if query_embedding:
                cached, cache_similarity = self.cache.get_semantic(
                    query_embedding, semantic_threshold, conversation_id=conversation_id
                )
                if cached:
                    cache_hit = "semantic"

        if cached:
            cached.cache_hit = cache_hit
            cached.cache_similarity = cache_similarity
            logger.info("Cache hit for prompt (%s, similarity=%s)", cache_hit, cache_similarity)
            if on_event:
                on_event({"type": "synthesis_done", "result": cached.to_dict(), "history_id": None})
            return cached

        context_blocks = []
        if conversation_context:
            context_blocks.append(f"Conversation so far:\n{conversation_context}")
        if file_context:
            context_blocks.append(f"Attached file content:\n{file_context}")

        working_query = prompt
        if context_blocks:
            working_query = "\n\n---\n\n".join(context_blocks) + f"\n\n---\n\nUser question: {prompt}"

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
        evaluations, evaluator_used, explanation = await llm_judge_refine(
            text_variant, responses, heuristic_scores, judge
        )
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
            explanation=explanation,
        )

        if effective_exact_cache or effective_semantic_cache:
            write_embedding = query_embedding if effective_semantic_cache else None
            write_conversation_id = conversation_id if conversation_context else None
            self.cache.set(prompt, result, embedding=write_embedding, conversation_id=write_conversation_id)
        history_id: int | None = None
        if record_history:
            history_id = self.history.record(result)

        if on_event:
            on_event({"type": "synthesis_done", "result": result.to_dict(), "history_id": history_id})

        return result
