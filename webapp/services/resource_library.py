from __future__ import annotations

import re
import zipfile
from io import BytesIO
from xml.etree import ElementTree


from ..extensions import db
from sqlalchemy import or_

from ..models import SafetyResourceDocument, SafetyResourceTextChunk


WORD_RE = re.compile(r"[a-z0-9]{3,}", re.I)
DOCX_TEXT_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"


def _plain_text_from_docx(binary_data: bytes) -> str:
    with zipfile.ZipFile(BytesIO(binary_data)) as archive:
        xml_data = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml_data)
    parts = [node.text or "" for node in root.iter(DOCX_TEXT_NS)]
    return " ".join(parts)


def _plain_text_from_pdf(binary_data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""

    reader = PdfReader(BytesIO(binary_data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_resource_text(filename: str, content_type: str | None, binary_data: bytes) -> str:
    lowered = filename.lower()
    if lowered.endswith((".txt", ".md", ".csv")) or (content_type or "").startswith("text/"):
        return binary_data.decode("utf-8", errors="ignore")
    if lowered.endswith(".docx"):
        try:
            return _plain_text_from_docx(binary_data)
        except (KeyError, zipfile.BadZipFile, ElementTree.ParseError):
            return ""
    if lowered.endswith(".pdf"):
        return _plain_text_from_pdf(binary_data)
    return ""


def split_resource_text(text: str, *, chunk_words: int = 180, overlap_words: int = 35) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    step = max(1, chunk_words - overlap_words)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_words]).strip()
        if len(chunk) >= 80:
            chunks.append(chunk)
        if start + chunk_words >= len(words):
            break
    return chunks


def rebuild_document_chunks(document: SafetyResourceDocument) -> int:
    SafetyResourceTextChunk.query.filter_by(document_id=document.id).delete()
    text = extract_resource_text(document.filename, document.content_type, document.binary_data)
    chunks = split_resource_text(text)
    for index, chunk in enumerate(chunks):
        db.session.add(
            SafetyResourceTextChunk(
                document_id=document.id,
                chunk_index=index,
                title=document.title or document.filename,
                topic=document.topic or "Digital safety",
                audience=document.audience or "all",
                text=chunk,
            )
        )
    return len(chunks)


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in WORD_RE.findall(text)}


def _document_scope_filter(family_id: int | None):
    if family_id is None:
        return SafetyResourceDocument.family_id.is_(None)
    return or_(
        SafetyResourceDocument.family_id.is_(None),
        SafetyResourceDocument.family_id == family_id,
    )


def search_resource_chunks(
    query: str,
    *,
    audience: str = "parent",
    family_id: int | None = None,
    limit: int = 3,
) -> list[dict]:
    query_tokens = _tokens(query)
    if not query_tokens:
        return []

    chunks = (
        SafetyResourceTextChunk.query.join(SafetyResourceDocument)
        .filter(SafetyResourceDocument.status == "approved")
        .filter(_document_scope_filter(family_id))
        .filter(SafetyResourceTextChunk.audience.in_(["all", audience]))
        .limit(50)
        .all()
    )
    if not chunks:
        chunks = (
            SafetyResourceTextChunk.query.join(SafetyResourceDocument)
            .filter(SafetyResourceDocument.status == "approved")
            .filter(_document_scope_filter(family_id))
            .filter(SafetyResourceTextChunk.audience.in_(["all", audience]))
            .order_by(SafetyResourceTextChunk.updated_at.desc())
            .limit(100)
            .all()
        )

    ranked = []
    for chunk in chunks:
        chunk_tokens = _tokens(f"{chunk.title} {chunk.topic} {chunk.text}")
        score = len(query_tokens & chunk_tokens)
        if score:
            ranked.append((score, chunk))

    ranked.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
    return [
        {
            "title": chunk.title,
            "topic": chunk.topic,
            "text": chunk.text,
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "score": score,
        }
        for score, chunk in ranked[:limit]
    ]


def summarize_resource_library(
    query: str,
    *,
    audience: str = "parent",
    family_id: int | None = None,
    limit: int = 4,
) -> dict | None:
    documents = (
        SafetyResourceDocument.query.filter(SafetyResourceDocument.status == "approved")
        .filter(_document_scope_filter(family_id))
        .filter(SafetyResourceDocument.audience.in_(["all", audience]))
        .order_by(SafetyResourceDocument.updated_at.desc())
        .limit(12)
        .all()
    )
    if not documents:
        return None

    query_tokens = _tokens(query)
    ranked = []
    for document in documents:
        doc_text = " ".join(
            str(part or "")
            for part in [document.title, document.filename, document.topic, document.summary]
        )
        score = len(query_tokens & _tokens(doc_text))
        ranked.append((score, document))
    ranked.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)

    selected = [document for _score, document in ranked[:limit]]
    summaries = []
    for document in selected:
        chunks = (
            SafetyResourceTextChunk.query.filter_by(document_id=document.id)
            .order_by(SafetyResourceTextChunk.chunk_index.asc())
            .limit(2)
            .all()
        )
        excerpt = document.summary or " ".join(chunk.text for chunk in chunks)
        excerpt = " ".join(str(excerpt or "").split())
        summaries.append(
            {
                "id": document.id,
                "title": document.title or document.filename,
                "topic": document.topic or "Digital safety",
                "audience": document.audience or "all",
                "summary": excerpt[:700] if excerpt else "No extractable text summary is available for this document yet.",
                "chunk_count": document.text_chunks.count(),
            }
        )

    return {
        "documents": summaries,
        "total_available": len(documents),
    }
