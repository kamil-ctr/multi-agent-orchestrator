"""POST /api/upload — extracts text from documents, or base64-encodes images
for the frontend to preview and later attach to a /api/query call."""
from __future__ import annotations

import base64

from fastapi import APIRouter, File, HTTPException, UploadFile

from core.file_extract import MAX_UPLOAD_BYTES, FileExtractionError, extract_text

router = APIRouter()

_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict:
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit")
    if not data:
        raise HTTPException(400, "Uploaded file is empty")

    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    is_image = ext in _IMAGE_EXTENSIONS or (file.content_type or "").startswith("image/")

    if is_image:
        mime_type = file.content_type or f"image/{'jpeg' if ext == 'jpg' else ext}"
        return {
            "kind": "image",
            "filename": filename,
            "mime_type": mime_type,
            "data_base64": base64.b64encode(data).decode("ascii"),
            "size_bytes": len(data),
        }

    try:
        text = extract_text(filename, data)
    except FileExtractionError as e:
        raise HTTPException(400, str(e)) from e

    preview = text[:300] + ("..." if len(text) > 300 else "")
    return {
        "kind": "file",
        "filename": filename,
        "content": text,
        "preview": preview,
        "size_bytes": len(data),
    }
