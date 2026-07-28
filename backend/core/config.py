"""Configuration loading: merges config.yaml with environment variables (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR  # kept for compatibility: config.yaml/data live under backend/
REPO_ROOT = BACKEND_DIR.parent  # multi_agent_orchestrator/ — the single shared .env lives here

load_dotenv(REPO_ROOT / ".env")


@dataclass
class AgentConfig:
    name: str
    enabled: bool
    model: str
    api_key_env: str
    timeout_s: float
    max_retries: int
    price_per_1k_input: float = 0.0
    price_per_1k_output: float = 0.0
    supports_vision: bool = False
    vision_model: str | None = None

    @property
    def effective_vision_model(self) -> str:
        return self.vision_model or self.model

    @property
    def api_key(self) -> str | None:
        return os.getenv(self.api_key_env) or None

    @property
    def is_available(self) -> bool:
        return self.enabled and bool(self.api_key)


@dataclass
class AppConfig:
    agents: dict[str, AgentConfig] = field(default_factory=dict)
    default_timeout_s: float = 15.0
    default_max_retries: int = 2
    cache_ttl_seconds: int = 3600
    judge_agent: str = "gemini"
    log_level: str = "INFO"
    data_dir: Path = PROJECT_ROOT / "data"
    top_n_for_synthesis: int = 3
    streaming_enabled: bool = True
    conversation_context_messages: int = 10
    conversation_context_max_tokens: int = 3000
    semantic_cache_enabled: bool = True
    semantic_cache_threshold: float = 0.92
    raw: dict[str, Any] = field(default_factory=dict)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def load_config(config_path: str | Path | None = None) -> AppConfig:
    path = Path(config_path) if config_path else PROJECT_ROOT / "config.yaml"
    raw = _load_yaml(path)

    defaults = raw.get("defaults", {})
    default_timeout = float(defaults.get("timeout_s", 15.0))
    default_retries = int(defaults.get("max_retries", 2))

    agents: dict[str, AgentConfig] = {}
    for name, spec in (raw.get("agents") or {}).items():
        agents[name] = AgentConfig(
            name=name,
            enabled=bool(spec.get("enabled", True)),
            model=spec.get("model", ""),
            api_key_env=spec.get("api_key_env", f"{name.upper()}_API_KEY"),
            timeout_s=float(spec.get("timeout_s", default_timeout)),
            max_retries=int(spec.get("max_retries", default_retries)),
            price_per_1k_input=float(spec.get("price_per_1k_input", 0.0)),
            price_per_1k_output=float(spec.get("price_per_1k_output", 0.0)),
            supports_vision=bool(spec.get("supports_vision", False)),
            vision_model=spec.get("vision_model"),
        )

    # DATA_DIR overrides config.yaml's data_dir — needed on platforms whose
    # free tier has no persistent disk (e.g. Render), where it's pointed at
    # /tmp: writable, but wiped on every restart/redeploy, so history and
    # cache don't survive across deploys there. Set DATA_DIR to a mounted
    # persistent-disk path on any platform that offers one.
    env_data_dir = os.getenv("DATA_DIR")
    data_dir = Path(env_data_dir) if env_data_dir else PROJECT_ROOT / raw.get("data_dir", "data")
    data_dir.mkdir(parents=True, exist_ok=True)

    streaming_enabled = os.getenv("STREAMING_ENABLED", "true").strip().lower() not in ("false", "0", "no")
    conversation_context_messages = int(os.getenv("CONVERSATION_CONTEXT_MESSAGES", "10"))
    conversation_context_max_tokens = int(os.getenv("CONVERSATION_CONTEXT_MAX_TOKENS", "3000"))
    semantic_cache_enabled = os.getenv("SEMANTIC_CACHE_ENABLED", "true").strip().lower() not in ("false", "0", "no")
    semantic_cache_threshold = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.92"))

    return AppConfig(
        agents=agents,
        default_timeout_s=default_timeout,
        default_max_retries=default_retries,
        cache_ttl_seconds=int(raw.get("cache_ttl_seconds", 3600)),
        judge_agent=raw.get("judge_agent", "gemini"),
        log_level=raw.get("log_level", "INFO"),
        data_dir=data_dir,
        top_n_for_synthesis=int(raw.get("top_n_for_synthesis", 3)),
        streaming_enabled=streaming_enabled,
        conversation_context_messages=conversation_context_messages,
        conversation_context_max_tokens=conversation_context_max_tokens,
        semantic_cache_enabled=semantic_cache_enabled,
        semantic_cache_threshold=semantic_cache_threshold,
        raw=raw,
    )
