# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project doesn't yet follow strict semantic versioning tags beyond marking the initial release.

## [Unreleased]

### Added
- Token-by-token streaming for all 4 agents: each adapter now supports a streaming call mode alongside the existing whole-response mode, relayed live over a new `agent_token` SSE event (`{agent, token}`); toggle via `STREAMING_ENABLED` (default true). A mid-stream failure (timeout, rate limit, network error) finalizes with whatever text was already streamed rather than discarding it — validated against a real timeout, not just a mocked one.
- Multi-turn conversation memory: new `conversations`/`messages` SQLite tables and `/api/conversations` endpoints (create, list, get, rename, delete, send message). Follow-up messages pass recent conversation history as context to every agent (capped at `CONVERSATION_CONTEXT_MESSAGES`, trimmed from the oldest once over `CONVERSATION_CONTEXT_MAX_TOKENS`); a conversation's title is generated asynchronously from its first message so the reply isn't blocked on it. The legacy `/api/query` endpoint still works, now creating a single-message conversation under the hood for backward compatibility. The Chat page's sidebar now lists conversations (rename/delete via right-click, client-side search) instead of individual query history.
- Semantic caching: a paraphrased repeat question now hits the cache too, not just an exact-text repeat. Implemented via Cohere's embed API and cosine similarity (`core/embeddings.py`) rather than a local `sentence-transformers`/PyTorch model — that combination adds 500MB+ of runtime, which would very likely OOM-kill the free-tier Render deployment (512MB RAM total); a hosted embed call keeps the deployment's memory footprint unchanged. Cohere's `embed-english-v3.0` was chosen after comparing real similarity scores against Mistral's embeddings API: Cohere cleanly separated true paraphrases (~0.94-0.96) from related-but-different questions (~0.7) and unrelated ones (~0.1); Mistral's embeddings compressed everything into a narrow band where an unrelated question could score *higher* than a true paraphrase, which wouldn't work with a fixed threshold. Cache entries are scoped per-conversation (or globally for standalone queries) so two different conversations asking the identical literal question can't cross-contaminate each other's cached answer. Toggle via `SEMANTIC_CACHE_ENABLED` / `SEMANTIC_CACHE_THRESHOLD` (server defaults) or per-request/per-browser via the new Settings → Caching section. Query responses now carry `cache_hit: "exact" | "semantic" | "miss"` and `cache_similarity`, surfaced in the UI as a badge. Validated against the real Cohere API, not mocked.
- Agent explainability panel: the judge prompt (`pipeline/evaluate.py`) now asks for a structured `_explanation` field — a 2-3 sentence `summary` plus a `key_differentiators` list of concrete, verifiable reasons (a specific fact one agent got right, a detail another omitted) — alongside its existing per-agent scores. `_extract_explanation()` parses this defensively: any missing or malformed field (non-dict, empty summary, non-list differentiators) returns `None` rather than a placeholder, since a fabricated rationale would be worse than none. Only populated when an LLM judge actually ran and produced well-formed output; single-agent runs and heuristic-only fallback both correctly leave it `None`. New `SynthesisExplanation` dataclass on `PipelineResult`, round-tripping through `to_dict()`/`from_dict()` for cache/history/conversation persistence. Frontend adds an `ExplainabilityPanel` — a collapsed-by-default "Why this synthesis?" toggle below the synthesized answer's metadata row — that renders nothing when the explanation is absent. Validated end-to-end against a real judge call (Mistral, substituted for the session's rate-limited Gemini) producing e.g. "Response 'b' is ranked higher due to its perfect accuracy..." with concrete differentiators.

### Changed
- Removed the 7 unused agent adapters (Claude, OpenAI, DeepSeek, Together AI, Grok, Perplexity, HuggingFace) and every "11 agents" branding reference; the project now consistently describes itself as multi-agent, backed by the 4 active providers (Gemini, Groq, Cohere, Mistral)
- Wired up native auto-deploy on both hosting platforms: Vercel was already git-connected but pointed at the repo root instead of `frontend/`; Render's GitHub App had never been installed on the account, so pushes silently never triggered a backend deploy

## [1.0.0] — 2026-07-28

Initial release: a full-stack multi-agent LLM orchestration platform, evolved from a single-model CLI prototype through a complete pipeline redesign, a web migration, and live-testing-driven hardening.

### Added

**Pipeline**
- Five-stage async pipeline: preprocess (query classification + prompt expansion) → parallel dispatch → normalize → evaluate → synthesize
- Plugin-based agent registry (`agents/registry.py`) using `pkgutil` auto-discovery — new providers require one adapter file and one config block, no core changes
- `BaseAgent` base class centralizing per-agent timeout, exponential-backoff retry, and latency tracking for every adapter
- Dependency-free heuristic evaluator scoring 5 dimensions (accuracy via cross-agent consensus, depth, clarity, relevance, conciseness) with zero network calls
- LLM-judge refinement layer that overrides heuristic scores and writes the synthesized answer with per-agent attribution, when ≥2 agents succeed and a judge is available
- Confidence scoring combining top score, cross-agent agreement (inverse variance), and success rate
- Graceful degradation throughout: missing keys, timeouts, rate limits, and malformed responses are caught and labeled, never crash the pipeline

**Multimodal input**
- Image upload routed directly to vision-capable agents; non-vision agents receive an auto-generated text description instead of being skipped
- Document upload (PDF via PyMuPDF, DOCX via python-docx, plain text/code otherwise) with extracted text injected as prompt context, 10MB cap
- Browser-native voice input (Web Speech API) and text-to-speech playback of synthesized answers — no external service

**Backend (FastAPI)**
- `POST /api/query` + `GET /api/query/{id}/stream` — background pipeline execution with Server-Sent Events streaming (`agent_start`/`agent_done`/`agent_error`/`synthesis_done`), replay-safe on reconnect
- `POST /api/upload`, `GET /api/history` (paginated + searchable), `GET /api/leaderboard` (filterable by query type), `GET /api/agents`, `GET /api/export/{id}` (Markdown/PDF)
- SQLite-backed prompt-hash response cache (TTL-based, bypassed for multimodal queries) and query history/leaderboard aggregation
- Per-request agent enable/disable filtering (`enabled_agents`) driven by the frontend Settings page

**Frontend (React + Vite + Tailwind v4)**
- Chat interface with live per-agent dispatch cards (color-coded, animated via Framer Motion), synthesized-answer panel with confidence gauge and attribution chips, sortable comparison table, and collapsible per-agent response cards with score breakdowns
- History sidebar (searchable, click-to-reload), Leaderboard page (Recharts bar chart + table), Settings page (agent toggles, key-configured status, theme, voice)
- Dark/light theming via CSS custom properties; validated accessible categorical color palette for agent identity (checked for CVD-safety and contrast)

**CLI**
- Rich-based terminal UI (`cli.py`) sharing the same `Orchestrator` as the web API — `ask`, `history`, `leaderboard`, `benchmark`, `export` commands

**Testing & tooling**
- 24 tests (`pytest` + `pytest-asyncio`) covering the heuristic evaluator, SQLite cache/TTL, query classification, concurrent dispatch under timeout/error/multimodal conditions, and end-to-end streaming orchestration — zero live network calls in the suite
- `start.sh` one-command dev startup for both servers

### Changed

- Migrated from a single-file Streamlit + Gemini prototype to the fully async multi-agent pipeline described above
- Restructured into `backend/` (FastAPI + pipeline) and `frontend/` (React) with a single shared root `.env`
- Fixed deprecated model references discovered via live API testing: Gemini (`gemini-2.5-flash` → `gemini-flash-latest`) and Cohere (`command-r` → `command-r-08-2024`, the former was retired 2025-09-15)

### Removed

- Trimmed the active agent roster from 11 configured providers to 4 verified-working ones (Gemini, Groq, Cohere, Mistral) after live end-to-end testing showed the other 7 blocked by account-side issues (insufficient credit/quota/balance, or no key configured) rather than code defects. All 7 adapters remain in the codebase, fully functional, and are re-activated by adding a key + config block — see the [Agent Compatibility Matrix](README.md#agent-compatibility-matrix).
