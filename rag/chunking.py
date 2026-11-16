"""Split PDF pages at regulatory clause boundaries, retaining provenance and overlap."""
from __future__ import annotations
import re
from typing import Any

_CLAUSE = re.compile(r"(?m)^\s*((?:\d+\.)+\d+(?:\([a-z]\))?)\s{1,}[^\n]+")

def chunk_pages(pages: list[dict[str, Any]], *, chunk_size: int = 1000, overlap: int = 150) -> list[dict[str, Any]]:
    if chunk_size <= 0: raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size: raise ValueError("overlap must be non-negative and smaller than chunk_size")
    result = []
    for page in pages:
        text = str(page.get("text", "")).strip()
        if not text: continue
        headings = list(_CLAUSE.finditer(text))
        spans = []
        if headings:
            if headings[0].start() > 0: spans.append((0, headings[0].start(), page.get("section")))
            for index, heading in enumerate(headings):
                end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
                spans.append((heading.start(), end, heading.group(1)))
        else:
            spans.append((0, len(text), page.get("section")))
        for span_start, span_end, section in spans:
            start = span_start
            while start < span_end:
                end = min(start + chunk_size, span_end)
                if end < span_end:
                    boundary = max(text.rfind("\n\n", start + chunk_size // 2, end), text.rfind(". ", start + chunk_size // 2, end), text.rfind(" ", start + chunk_size // 2, end))
                    if boundary > start: end = boundary + 1
                piece = text[start:end].strip()
                if piece:
                    item = {key: page.get(key) for key in ("source", "source_path", "document_version", "page")}
                    item.update({"section": section, "text": piece, "start_char": start, "end_char": end})
                    result.append(item)
                if end >= span_end: break
                start = max(start + 1, end - overlap)
    return result
