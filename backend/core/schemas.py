"""Common data schemas shared across the pipeline stages."""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class QueryType(str, Enum):
    FACTUAL = "factual"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    CODING = "coding"
    CONVERSATIONAL = "conversational"


class AgentStatus(str, Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    DISABLED = "disabled"
    RATE_LIMITED = "rate_limited"


@dataclass
class ImageInput:
    """A base64-encoded image attached to a query, handed to vision-capable
    agents as-is and summarized into text context for everyone else."""

    mime_type: str
    data_base64: str


@dataclass
class AgentResponse:
    """Normalized response schema every agent adapter must produce."""

    agent: str
    status: AgentStatus
    response_text: str | None = None
    latency_ms: float | None = None
    token_count_estimate: int | None = None
    error: str | None = None
    retries: int = 0
    model: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AgentResponse":
        d = dict(d)
        d["status"] = AgentStatus(d["status"])
        return cls(**d)


@dataclass
class EvaluationScore:
    agent: str
    accuracy: float
    depth: float
    clarity: float
    relevance: float
    conciseness: float
    overall: float
    strengths: str = ""
    weaknesses: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EvaluationScore":
        return cls(**d)


@dataclass
class SynthesisExplanation:
    """Why the judge prioritized certain agents' responses over others.

    Populated only when an LLM judge actually ran and produced well-formed
    output for this extra field — never a placeholder when unavailable,
    since a fabricated "explanation" would be worse than none at all.
    """

    summary: str
    key_differentiators: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SynthesisExplanation":
        return cls(**d)


@dataclass
class PipelineResult:
    query: str
    query_type: str
    expanded_query: str
    agent_responses: list[AgentResponse]
    evaluations: list[EvaluationScore]
    synthesized_answer: str
    attribution: dict[str, str]
    confidence_score: float
    total_latency_ms: float
    total_tokens_estimate: int
    estimated_cost_usd: float
    cached: bool = False
    cache_hit: str = "miss"  # "exact" | "semantic" | "miss"
    cache_similarity: float | None = None
    evaluator_used: str = "heuristic"
    explanation: SynthesisExplanation | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "query_type": self.query_type,
            "expanded_query": self.expanded_query,
            "agent_responses": [r.to_dict() for r in self.agent_responses],
            "evaluations": [e.to_dict() for e in self.evaluations],
            "synthesized_answer": self.synthesized_answer,
            "attribution": self.attribution,
            "confidence_score": self.confidence_score,
            "total_latency_ms": self.total_latency_ms,
            "total_tokens_estimate": self.total_tokens_estimate,
            "estimated_cost_usd": self.estimated_cost_usd,
            "cached": self.cached,
            "cache_hit": self.cache_hit,
            "cache_similarity": self.cache_similarity,
            "evaluator_used": self.evaluator_used,
            "explanation": self.explanation.to_dict() if self.explanation else None,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PipelineResult":
        explanation = d.get("explanation")
        return cls(
            query=d["query"],
            query_type=d["query_type"],
            expanded_query=d["expanded_query"],
            agent_responses=[AgentResponse.from_dict(r) for r in d["agent_responses"]],
            evaluations=[EvaluationScore.from_dict(e) for e in d["evaluations"]],
            synthesized_answer=d["synthesized_answer"],
            attribution=d["attribution"],
            confidence_score=d["confidence_score"],
            total_latency_ms=d["total_latency_ms"],
            total_tokens_estimate=d["total_tokens_estimate"],
            estimated_cost_usd=d["estimated_cost_usd"],
            cached=d.get("cached", False),
            cache_hit=d.get("cache_hit", "miss"),
            cache_similarity=d.get("cache_similarity"),
            evaluator_used=d.get("evaluator_used", "heuristic"),
            explanation=SynthesisExplanation.from_dict(explanation) if explanation else None,
            timestamp=d.get("timestamp", time.time()),
        )
