"""Read PDFs page-by-page with provenance and a content version for incremental indexing."""
from __future__ import annotations
import hashlib,re
from pathlib import Path
from typing import Any
DEFAULT_DOCUMENT_DIRS=(Path("documents/dgca"),Path("documents/airline"))
_SECTION_RE=re.compile(r"^\s*((?:section|chapter|article|rule|regulation|3\.\d+(?:\.\d+)*)\s+[\w.()/-]+[^\n]*)\s*$",re.I|re.M)
def load_pdfs(directories: tuple[str|Path,...]|list[str|Path]|None=None)->list[dict[str,Any]]:
    try: from pypdf import PdfReader
    except ImportError as exc: raise RuntimeError("PDF loading requires pypdf") from exc
    roots=[Path(p) for p in directories] if directories is not None else list(DEFAULT_DOCUMENT_DIRS)
    pages=[]
    for root in roots:
        if not root.exists(): continue
        for path in sorted(root.rglob("*.pdf")):
            content_hash=hashlib.sha256(path.read_bytes()).hexdigest()
            try: source_key=path.resolve().as_posix()
            except OSError: source_key=str(path.as_posix())
            for number,page in enumerate(PdfReader(str(path)).pages,start=1):
                text=(page.extract_text() or "").strip()
                if not text: continue
                headings=_SECTION_RE.findall(text)
                pages.append({"text":text,"source":path.name,"source_path":source_key,"document_version":content_hash,"page":number,"section":headings[-1].strip() if headings else None})
    return pages
