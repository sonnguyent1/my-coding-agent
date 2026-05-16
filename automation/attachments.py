"""Download Trello card attachments and persist them as GitHub Actions temp files.

Temp directory resolution (in priority order):
  1. $RUNNER_TEMP  — set by the GitHub Actions runner
  2. $TMPDIR / system temp  — local fallback for development

Downloaded files land in:  <temp_dir>/trello_attachments/<safe_filename>
"""
from __future__ import annotations

import logging
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from automation.models import TrelloAttachment
from automation.trello import api_client

logger = logging.getLogger(__name__)

# Attachments larger than this are skipped to avoid memory and token bloat.
_MAX_BYTES = 512 * 1024  # 512 KB

# How many characters of text content to surface in the planning context.
_CONTEXT_SNIPPET_CHARS = 2_000

# MIME types we attempt to download and persist.
_SUPPORTED_MIME_PREFIXES = (
    "text/",            # plain text, CSV, HTML, XML, CSS, …
    "application/pdf",  # PDF documents
    "image/",           # JPEG, PNG, GIF, WebP, SVG, …
    "application/json",
    "application/xml",
)

# Subset of the above that can be decoded as UTF-8 for the planning context snippet.
_TEXT_MIME_PREFIXES = (
    "text/",
    "application/json",
    "application/xml",
)


@dataclass(frozen=True)
class DownloadedAttachment:
    name: str
    file_name: str
    mime_type: str
    local_path: str
    """Absolute path to the file on disk."""
    content_snippet: str
    """First ~2 000 chars of decoded text, empty for binary files."""


def _temp_dir() -> Path:
    """Return the best available temp directory for GitHub Actions."""
    runner_temp = os.environ.get("RUNNER_TEMP")
    base = Path(runner_temp) if runner_temp else Path(tempfile.gettempdir())
    dest = base / "trello_attachments"
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def _safe_filename(name: str) -> str:
    """Sanitize a filename so it is safe for all platforms."""
    sanitized = re.sub(r"[^\w.\-]", "_", name)
    return sanitized[:200] or "attachment"


def _is_supported(mime_type: str) -> bool:
    return any(mime_type.startswith(prefix) for prefix in _SUPPORTED_MIME_PREFIXES)


def _is_text(mime_type: str) -> bool:
    return any(mime_type.startswith(prefix) for prefix in _TEXT_MIME_PREFIXES)


def download_card_attachments(
    attachments: list[TrelloAttachment],
    dest_dir: Path | None = None,
) -> list[DownloadedAttachment]:
    """Download *attachments* from Trello and write them to *dest_dir*.

    Returns a list of :class:`DownloadedAttachment` for every file that was
    successfully downloaded.  Files that fail to download are logged and
    skipped so the orchestrator can continue.
    """
    if not attachments:
        return []

    dest = dest_dir if dest_dir is not None else _temp_dir()
    dest.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %d attachment(s) to %s", len(attachments), dest)

    results: list[DownloadedAttachment] = []

    for attachment in attachments:
        if attachment.is_malicious:
            logger.warning("Skipping malicious attachment: %s", attachment.name)
            continue

        if not _is_supported(attachment.mime_type):
            logger.debug("Skipping unsupported MIME type '%s' for attachment: %s", attachment.mime_type, attachment.name)
            continue

        safe_name = _safe_filename(attachment.file_name or attachment.name)
        local_path = dest / safe_name

        try:
            raw = api_client.download_attachment(attachment.url, max_bytes=_MAX_BYTES)
        except RuntimeError as exc:
            logger.warning("Failed to download attachment '%s': %s", attachment.name, exc)
            continue

        local_path.write_bytes(raw)
        logger.info(
            "Saved attachment '%s' → %s (%d bytes)",
            attachment.name,
            local_path,
            len(raw),
        )

        snippet = ""
        if _is_text(attachment.mime_type):
            try:
                snippet = raw.decode("utf-8", errors="replace")[:_CONTEXT_SNIPPET_CHARS]
            except Exception:
                pass

        results.append(
            DownloadedAttachment(
                name=attachment.name,
                file_name=safe_name,
                mime_type=attachment.mime_type,
                local_path=str(local_path),
                content_snippet=snippet,
            )
        )

    logger.info("Downloaded %d / %d attachment(s) successfully", len(results), len(attachments))
    return results
