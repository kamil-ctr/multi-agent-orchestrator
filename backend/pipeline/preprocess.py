"""Stage 1 — Query Preprocessing.

Classifies the query type with a fast keyword heuristic (no API call needed,
works fully offline) and optionally expands/clarifies the prompt using a
lightweight model call before dispatch. If no agent is available, the
original prompt passes through untouched — this stage must never block the
pipeline.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from agents.base import BaseAgent
from core.logger import get_logger
from core.schemas import QueryType

logger = get_logger(__name__)

_CODING_HINTS = re.compile(
    r"\b(code|function|python|javascript|java|c\+\+|typescript|debug|bug|"
    r"algorithm|implement|compile|stack trace|regex|sql query|refactor|"
    r"class |def |import |api endpoint)\b|```",
    re.IGNORECASE,
)
_CREATIVE_HINTS = re.compile(
    r"\b(write a (story|poem|song|screenplay)|imagine|fiction|poem|"
    r"creative|metaphor|brainstorm names|make up a|invent a)\b",
    re.IGNORECASE,
)
_ANALYTICAL_HINTS = re.compile(
    r"\b(compare|analy[sz]e|pros and cons|evaluate|trade-?offs?|why does|"
    r"impact of|implications|which is better|assess|critique)\b",
    re.IGNORECASE,
)
_FACTUAL_HINTS = re.compile(
    r"^(what|who|when|where|which|how many|how much|define|is |does |"
    r"capital of|explain|describe|tell me about|summarize|summarise|"
    r"list |outline)\b",
    re.IGNORECASE,
)
_CONVERSATIONAL_HINTS = re.compile(
    r"^(hi|hello|hey|how are you|thanks|thank you|good morning|good evening)\b",
    re.IGNORECASE,
)

# Expected characteristics used later by the evaluator to calibrate what
# "good depth" / "good conciseness" look like for this kind of query.
EXPECTED_CHARACTERISTICS: dict[QueryType, dict[str, str]] = {
    QueryType.FACTUAL: {"expected_length": "short", "priority": "accuracy"},
    QueryType.CREATIVE: {"expected_length": "long", "priority": "clarity"},
    QueryType.ANALYTICAL: {"expected_length": "long", "priority": "depth"},
    QueryType.CODING: {"expected_length": "medium", "priority": "accuracy"},
    QueryType.CONVERSATIONAL: {"expected_length": "short", "priority": "clarity"},
}


def classify_query_type(prompt: str) -> QueryType:
    """Classify a prompt into a QueryType using keyword/regex heuristics only.

    No network call is made — this must stay instant and fully offline since
    it runs on every query before any agent is contacted.

    Args:
        prompt: The raw user prompt (before expansion).

    Returns:
        The best-matching QueryType. Falls back to FACTUAL for anything
        substantive that isn't clearly a greeting, and CONVERSATIONAL only
        for actual small talk (matched via _CONVERSATIONAL_HINTS).
    """
    text = prompt.strip()
    if _CODING_HINTS.search(text):
        return QueryType.CODING
    if _CREATIVE_HINTS.search(text):
        return QueryType.CREATIVE
    if _ANALYTICAL_HINTS.search(text):
        return QueryType.ANALYTICAL
    if _CONVERSATIONAL_HINTS.search(text):
        return QueryType.CONVERSATIONAL
    if _FACTUAL_HINTS.search(text) or text.endswith("?"):
        return QueryType.FACTUAL
    # Anything substantive that didn't match a greeting is more likely a
    # terse factual ask than small talk — reserve CONVERSATIONAL for actual chit-chat.
    return QueryType.FACTUAL


@dataclass
class PreprocessResult:
    original_prompt: str
    expanded_prompt: str
    query_type: QueryType
    characteristics: dict[str, str]
    was_expanded: bool


_EXPANSION_INSTRUCTION = (
    "Rewrite the following user prompt to be maximally clear and unambiguous "
    "for downstream AI models to answer. Preserve the original intent and "
    "language exactly — do not answer it, do not add new questions, only "
    "clarify vague references and fill in obviously implied context. "
    "Output ONLY the rewritten prompt, nothing else.\n\nPrompt: "
)


async def expand_query(prompt: str, expander: BaseAgent | None) -> tuple[str, bool]:
    """Rewrite a prompt to be clearer/less ambiguous via a lightweight LLM call.

    This is a best-effort enhancement, never a hard dependency: if no expander
    agent is available, the call fails, or the result looks degenerate (empty
    or wildly longer than the source), the original prompt is returned
    unchanged rather than blocking or failing the pipeline.

    Args:
        prompt: The raw user prompt to expand.
        expander: The agent to use for expansion (typically the configured
            judge agent), or None to skip expansion entirely.

    Returns:
        A (text, was_expanded) tuple — was_expanded is False whenever the
        original prompt was kept as-is.
    """
    if expander is None or not expander.is_available:
        return prompt, False

    response = await expander.generate(_EXPANSION_INSTRUCTION + prompt)
    if response.response_text and response.response_text.strip():
        expanded = response.response_text.strip().strip('"')
        # Guard against degenerate expansions (empty, or wildly longer than the source).
        if 0 < len(expanded) < max(400, len(prompt) * 6):
            return expanded, True

    logger.debug("Query expansion unavailable/degenerate, using original prompt")
    return prompt, False


async def preprocess(prompt: str, expander: BaseAgent | None = None) -> PreprocessResult:
    """Run Stage 1 end-to-end: classify the query type and expand the prompt.

    Args:
        prompt: The raw user prompt.
        expander: Optional agent used to expand/clarify the prompt; passed
            straight through to expand_query (see its docstring for the
            offline-safe fallback behavior).

    Returns:
        A PreprocessResult bundling the original and expanded prompt, the
        classified QueryType, and the characteristics the evaluator should
        expect for that type.
    """
    query_type = classify_query_type(prompt)
    expanded, was_expanded = await expand_query(prompt, expander)
    return PreprocessResult(
        original_prompt=prompt,
        expanded_prompt=expanded,
        query_type=query_type,
        characteristics=EXPECTED_CHARACTERISTICS[query_type],
        was_expanded=was_expanded,
    )
