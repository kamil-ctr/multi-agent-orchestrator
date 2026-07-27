"""GET /api/export/{id}?format=md|pdf — download a past query's report."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from ui.export import export_markdown, export_pdf

router = APIRouter()

_EXPORT_DIR = Path(tempfile.gettempdir()) / "multi_agent_orchestrator_exports"


@router.get("/export/{query_id}")
async def export_query(query_id: int, request: Request, format: str = "md") -> FileResponse:
    if format not in ("md", "pdf"):
        raise HTTPException(400, "format must be 'md' or 'pdf'")

    orch = request.app.state.orchestrator
    entry = orch.history.get(query_id)
    if entry is None:
        raise HTTPException(404, f"No history entry with id {query_id}")

    result = entry.result()
    _EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _EXPORT_DIR / f"query_{query_id}.{format}"

    if format == "md":
        export_markdown(result, out_path)
        media_type = "text/markdown"
    else:
        try:
            export_pdf(result, out_path)
        except RuntimeError as e:
            raise HTTPException(500, str(e)) from e
        media_type = "application/pdf"

    return FileResponse(out_path, media_type=media_type, filename=out_path.name)
