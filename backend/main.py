"""FastAPI entrypoint.

    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import agents as agents_api
from api import export as export_api
from api import history as history_api
from api import leaderboard as leaderboard_api
from api import query as query_api
from api import upload as upload_api
from core.config import load_config
from core.logger import setup_logging
from pipeline.orchestrator import Orchestrator

config = load_config()
setup_logging(config.log_level)

app = FastAPI(title="Multi-Agent Orchestration API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.orchestrator = Orchestrator(config)

app.include_router(query_api.router, prefix="/api")
app.include_router(upload_api.router, prefix="/api")
app.include_router(history_api.router, prefix="/api")
app.include_router(leaderboard_api.router, prefix="/api")
app.include_router(agents_api.router, prefix="/api")
app.include_router(export_api.router, prefix="/api")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "agents_available": sum(app.state.orchestrator.availability().values())}
