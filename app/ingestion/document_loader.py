"""Document loader for PDF, TXT, and user-provided research text.

Supports:
- PDF extraction using pypdf with detection of encrypted, scanned/empty, and malformed files.
- Safe plain-text decoding (UTF-8, Latin-1, CP1252) and normalization.
- Stable document ID generation and sentence-level evidence tagging.
"""

from __future__ import annotations

import io
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import pypdf
from pypdf.errors import PdfReadError

from app.models import Paper, SentenceSpan, PicoBadges
from app.ingestion.sentence_tagger import tag_sentences
from app.ingestion.paste_parser import parse_pasted_text

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
MAX_PAGE_COUNT = 60
MAX_WORD_COUNT = 60000


class DocumentIngestionError(Exception):
    """Custom exception raised for invalid, unsupported, or malformed uploaded documents."""
    pass


def extract_text_from_pdf(file_bytes: bytes, filename: str = "document.pdf") -> Tuple[str, Dict[str, Any]]:
    """Extracts text from PDF bytes with safety checks for encryption, corruption, and scanned pages."""
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise DocumentIngestionError(
            f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )

    if not file_bytes:
        raise DocumentIngestionError("Uploaded PDF file is empty (0 bytes).")

    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    except (PdfReadError, Exception) as exc:
        raise DocumentIngestionError(f"Malformed or corrupt PDF file: {exc}")

    if reader.is_encrypted:
        raise DocumentIngestionError(
            "Encrypted/password-protected PDF detected. Please provide an unencrypted document."
        )

    num_pages = len(reader.pages)
    if num_pages == 0:
        raise DocumentIngestionError("PDF contains zero pages.")

    if num_pages > MAX_PAGE_COUNT:
        raise DocumentIngestionError(
            f"PDF has {num_pages} pages, which exceeds the supported limit of {MAX_PAGE_COUNT} pages."
        )

    text_parts: List[str] = []
    has_images = False

    for page_idx, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text.strip())
            if len(page.images) > 0:
                has_images = True
        except Exception:
            continue

    combined_text = "\n\n".join(text_parts).strip()

    # Detect scanned / image-only PDFs
    if not combined_text:
        if has_images:
            raise DocumentIngestionError(
                "Scanned or image-only PDF detected. Text extraction requires searchable text (OCR is not supported)."
            )
        else:
            raise DocumentIngestionError("PDF contains no readable text.")

    # Extract basic metadata if available
    metadata: Dict[str, Any] = {"num_pages": num_pages}
    if reader.metadata:
        if reader.metadata.title:
            metadata["title"] = str(reader.metadata.title).strip()
        if reader.metadata.author:
            metadata["author"] = str(reader.metadata.author).strip()

    return combined_text, metadata


def extract_text_from_txt(file_bytes: bytes, filename: str = "document.txt") -> Tuple[str, Dict[str, Any]]:
    """Decodes plain text bytes safely across common encodings."""
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise DocumentIngestionError(
            f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )

    if not file_bytes:
        raise DocumentIngestionError("Uploaded text file is empty (0 bytes).")

    decoded_text = ""
    for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            decoded_text = file_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if not decoded_text:
        raise DocumentIngestionError("Failed to decode text file. Unsupported character encoding.")

    # Normalize line endings and multiple spaces
    normalized = decoded_text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized).strip()

    if not normalized:
        raise DocumentIngestionError("Text file contains only whitespace.")

    return normalized, {"num_pages": 1}


def ingest_document(
    file_bytes: Optional[bytes] = None,
    raw_text: Optional[str] = None,
    filename: Optional[str] = None,
    user_title: Optional[str] = None,
    mime_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Universal ingestion pipeline for PDFs, TXT files, and raw pasted abstracts.

    Returns a normalized document object with stable ID, metadata, sentence spans, and PICO.
    """
    clean_filename = (filename or "document.txt").strip()
    ext = os.path.splitext(clean_filename)[1].lower()

    metadata: Dict[str, Any] = {}
    content_text = ""
    doc_type = "Direct Ingestion"

    if file_bytes is not None:
        if ext == ".pdf" or mime_type == "application/pdf":
            content_text, metadata = extract_text_from_pdf(file_bytes, clean_filename)
            doc_type = "PDF Upload"
        elif ext in [".txt", ".text", ".md"] or (mime_type and "text" in mime_type):
            content_text, metadata = extract_text_from_txt(file_bytes, clean_filename)
            doc_type = "TXT Upload"
        else:
            raise DocumentIngestionError(
                f"Unsupported file format '{ext}'. Only PDF (.pdf) and Plain Text (.txt) files are supported."
            )
    elif raw_text is not None:
        normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized:
            raise DocumentIngestionError("Pasted abstract text cannot be empty.")
        content_text = normalized
        doc_type = "Pasted Abstract"
        metadata = {"num_pages": 1}
    else:
        raise DocumentIngestionError("Neither file content nor raw text was provided for ingestion.")

    words = content_text.split()
    word_count = len(words)
    if word_count > MAX_WORD_COUNT:
        raise DocumentIngestionError(
            f"Document contains {word_count} words, which exceeds the limit of {MAX_WORD_COUNT} words."
        )

    # Determine title
    title = ""
    if user_title and user_title.strip():
        title = user_title.strip()
    elif metadata.get("title"):
        title = metadata["title"]
    else:
        # Infer title from first line if reasonably short, otherwise filename
        first_line = content_text.split("\n")[0].strip()
        if 10 < len(first_line) <= 120 and not first_line.lower().startswith("background"):
            title = first_line
        else:
            base_name = os.path.splitext(clean_filename)[0].replace("_", " ").replace("-", " ")
            title = base_name.capitalize() if base_name else "User Uploaded Evidence"

    # Stable Document Identifier
    doc_id = f"doc_{int(time.time())}_{abs(hash(clean_filename + content_text[:50])) % 10000}"

    # Sentence tagging and PICO extraction
    sentences, pico = parse_pasted_text(content_text)

    # Paper object for system interoperability
    paper_record = Paper(
        id=doc_id,
        title=title,
        authors=metadata.get("author", "User Document"),
        journal=f"{doc_type} ({metadata.get('num_pages', 1)} pages)",
        date=time.strftime("%d %b %Y"),
        type=doc_type,
        source="Upload" if "Upload" in doc_type else "Paste",
        tag="User Evidence",
        tone="peach" if "PDF" in doc_type else "mint",
        abstract=content_text,
        pmid_doi=f"FILE · {clean_filename}" if filename else f"ID · {doc_id}",
    )

    preview_text = content_text[:400] + ("…" if len(content_text) > 400 else "")

    return {
        "doc_id": doc_id,
        "title": title,
        "filename": clean_filename,
        "doc_type": doc_type,
        "word_count": word_count,
        "page_count": metadata.get("num_pages", 1),
        "preview_text": preview_text,
        "full_text": content_text,
        "paper": paper_record,
        "sentences": sentences,
        "pico": pico,
    }
