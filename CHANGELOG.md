# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project doesn't yet follow strict semantic versioning tags beyond marking the initial release.

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
