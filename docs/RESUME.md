# Resume Material

Ready-to-use copy for a resume, LinkedIn projects section, or portfolio site. Pick the bullets that fit the role you're applying for — the four below cover different angles (systems design, scale/integration breadth, evaluation/ML-adjacent work, and testing rigor) so you rarely need all four at once.

## Project Title

**Multi-Agent Orchestrator** — a full-stack platform that queries multiple LLM providers in parallel and synthesizes their responses into one cross-validated answer.

## Resume Bullets

Use 2–3 of these, not all 4, depending on whether the role emphasizes backend systems, integration breadth, or evaluation logic:

> Architected a full-stack multi-agent LLM orchestration platform dispatching prompts to 4 concurrent LLM providers (Gemini, Groq, Cohere, Mistral) behind one async Python pipeline, with sub-3-second parallel response times via `asyncio` and per-agent timeout/retry with exponential backoff.

> Designed a plugin-based agent registry using Python's `pkgutil` for zero-config provider discovery, so a new LLM integration requires one adapter file and one config block with no changes to core orchestration logic — validated in production by integrating and later retiring multiple independent providers without ever modifying orchestration code.

> Built a hybrid evaluation engine combining a dependency-free heuristic scorer (5 independent dimensions: accuracy, depth, clarity, relevance, conciseness) with LLM-judge refinement, achieving 85–93% synthesis confidence by cross-validating responses across independent models — caught and down-weighted a factually incorrect response that scored well on purely structural heuristics.

> Implemented real-time streaming with FastAPI, Server-Sent Events, and React to surface live per-agent status (waiting → running → done/error) end-to-end, backed by a 24-test `pytest`/`pytest-asyncio` suite covering concurrent dispatch, timeout/retry behavior, and full pipeline correctness with zero live network calls in CI.

## LaTeX Resume Section

Drop-in for a standard `itemize`-based resume (adjust the heading macro to match your template — this uses plain `\textbf`/`\textit` so it works without any custom resume class):

```latex
\textbf{Multi-Agent Orchestrator} $\vert$ \textit{Python, FastAPI, React, asyncio, SQLite, SSE} \hfill 2026 \\
\textit{github.com/kamil-ctr/multi-agent-orchestrator}
\begin{itemize}
    \item Architected a full-stack multi-agent LLM orchestration platform dispatching prompts to 4 concurrent LLM providers behind one async pipeline, with sub-3-second parallel response times via \texttt{asyncio} and per-agent timeout/retry with exponential backoff.
    \item Designed a plugin-based agent registry using Python's \texttt{pkgutil} for zero-config provider discovery, validated by integrating and later retiring multiple independent providers without modifying a single existing file.
    \item Built a hybrid evaluation engine (heuristic scorer + LLM-judge refinement) achieving 85--93\% synthesis confidence by cross-validating responses across independent models.
    \item Implemented real-time streaming with FastAPI, Server-Sent Events, and React; backed by a 24-test \texttt{pytest} suite with zero live network calls in CI.
\end{itemize}
```

If your template uses a custom `\resumeProjectHeading` or similar macro (common in the Jake Gutierrez / Awesome-CV style templates), swap the first two lines for that macro's call signature and keep the `itemize` block as-is.

## LinkedIn "Projects" Section

LinkedIn's Projects section has a title, date, description, and optional link/skills fields. Shorter and less jargon-dense than the resume bullets, since it's read by a broader audience:

**Title:** Multi-Agent Orchestrator

**Date:** 2026

**Description:**
> Full-stack app that sends one prompt to multiple AI models (Gemini, Groq, Cohere, Mistral) in parallel, scores every response on five dimensions, and synthesizes them into a single answer with source attribution — instead of trusting one model's take, you get a cross-checked one. Built with a Python/FastAPI backend streaming live results over Server-Sent Events to a React frontend, with support for image and document uploads and voice input/output. Designed the provider integration as a plugin system — adding a new AI model takes one file, no changes anywhere else. 24 automated tests, fully async pipeline, sub-3-second parallel dispatch.

**Skills:** Python, FastAPI, React, asyncio, Server-Sent Events, SQLite, REST API Design, System Architecture, Prompt Engineering, Test-Driven Development

**Link:** `github.com/kamil-ctr/multi-agent-orchestrator`
