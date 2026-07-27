"""Extracts plain text from uploaded files so it can be prepended to a
prompt as context. Supports pdf, docx, and anything readable as UTF-8 text
(txt/md/csv/json/code files)."""
from __future__ import annotations

import io

from core.logger import get_logger

logger = get_logger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB

_PLAIN_TEXT_EXTENSIONS = {
    "txt", "md", "csv", "json", "py", "js", "jsx", "ts", "tsx", "java", "c",
    "cpp", "h", "hpp", "go", "rs", "rb", "php", "html", "css", "yaml", "yml",
    "sh", "sql", "xml", "toml", "ini", "log",
}

MAX_EXTRACTED_CHARS = 20_000  # keep prompts from ballooning past model context windows


class FileExtractionError(ValueError):
    pass


def _extract_pdf(data: bytes) -> str:
    import fitz  # PyMuPDF

    text_parts = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def _extract_docx(data: bytes) -> str:
    import docx

    document = docx.Document(io.BytesIO(data))
    return "\n".join(p.text for p in document.paragraphs)


def _extract_plain(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="replace")


def extract_text(filename: str, data: bytes) -> str:
    if len(data) > MAX_UPLOAD_BYTES:
        raise FileExtractionError(f"File exceeds the {MAX_UPLOAD_BYTES // (1024*1024)}MB limit")

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    try:
        if ext == "pdf":
            text = _extract_pdf(data)
        elif ext == "docx":
            text = _extract_docx(data)
        elif ext in _PLAIN_TEXT_EXTENSIONS or ext == "":
            text = _extract_plain(data)
        else:
            raise FileExtractionError(f"Unsupported file type: .{ext}")
    except FileExtractionError:
        raise
    except Exception as e:  # noqa: BLE001 — any parser failure must surface as a clean 4xx, not crash
        logger.warning("Failed to extract text from %s: %s", filename, e)
        raise FileExtractionError(f"Could not read {filename}: {e}") from e

    if len(text) > MAX_EXTRACTED_CHARS:
        text = text[:MAX_EXTRACTED_CHARS] + "\n\n[...truncated...]"
    return text.strip()
