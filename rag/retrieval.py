"""Idempotent, incremental PDF indexing and cached FAISS retrieval."""
from __future__ import annotations
import argparse,hashlib,json,os,time
from functools import lru_cache
from pathlib import Path
from typing import Any
from .chunking import chunk_pages
from .document_loader import load_pdfs
from .embeddings import SentenceTransformerEmbedder
from .vector_store import FaissVectorStore
_EMBEDDER=SentenceTransformerEmbedder()
@lru_cache(maxsize=1)
def _store():
    store=FaissVectorStore(os.getenv("RAG_INDEX_PATH","data/rag/faiss.index"))
    if store.index_path.exists(): store.load()
    return store

def _chunk_id(item):
    key="|".join(str(item.get(k,"")) for k in ("source_path","document_version","page","start_char")) + "|" + str(item.get("text",""))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
def rebuild_index(directories:tuple[str|Path,...]|list[str|Path]|None=None,*,chunk_size:int=1000,overlap:int=150,incremental:bool=True,reembed:bool=False)->int:
    embedded=0
    started=time.perf_counter(); pages=load_pdfs(directories); chunks=chunk_pages(pages,chunk_size=chunk_size,overlap=overlap)
    if not chunks and not reembed: raise ValueError("No extractable PDF pages found in configured document directories")
    for item in chunks:item["chunk_id"]=_chunk_id(item)
    path=os.getenv("RAG_INDEX_PATH","data/rag/faiss.index"); store=FaissVectorStore(path)
    if store.index_path.exists(): store.load()
    if reembed:
        active=store.active_records() if store._records else chunks
        vectors=_EMBEDDER.encode([item["text"] for item in active])
        store.build(vectors,active)
        embedded=len(active)
        chunks=active
    known=store.known_chunk_ids() if incremental and not reembed else set()
    new_chunks=[item for item in chunks if item["chunk_id"] not in known]
    if reembed:
        pass
    elif not incremental or not store.index_path.exists():
        vectors=_EMBEDDER.encode([item["text"] for item in chunks]); store.build(vectors,chunks); embedded=len(chunks)
    elif new_chunks:
        vectors=_EMBEDDER.encode([item["text"] for item in new_chunks]); store.append_incremental(vectors,new_chunks); embedded=len(new_chunks)
    # Content removal: retire old chunks whose source disappeared from this corpus.
    present={str(p.get("source_path")) for p in pages}
    for item in store._records:
        if str(item.get("source_path")) not in present:item["active"]=False
    elapsed=max(time.perf_counter()-started,1e-9)
    store.set_manifest(embedding_model_version=_EMBEDDER.model_name or "signed-hash-v1",corpus_sources=sorted(present),embedding_strategy="sentence-transformers" if _EMBEDDER.model_name else "local deterministic signed feature hashing",embedding_model_configured=bool(_EMBEDDER.model_name),chunk_size=chunk_size,overlap=overlap,documents=len(present),last_pipeline_seconds=elapsed,last_pipeline_chunks_per_second=embedded/elapsed)
    store.save(); _store.cache_clear()
    try:
        from app.metrics import INDEX_CHUNKS,INDEX_BUILD_SECONDS,INDEX_CHUNKS_PER_SECOND,INDEX_AGE
        INDEX_CHUNKS.set(len(store.active_records())); INDEX_BUILD_SECONDS.set(elapsed); INDEX_CHUNKS_PER_SECOND.set(embedded/elapsed); INDEX_AGE.set(0)
    except Exception: pass
    return len(store.active_records())
def _lexical_score(query:str,record:dict[str,Any])->float:
    import re
    text=(str(record.get("text",""))+" "+str(record.get("section",""))).lower()
    normalized=query.lower()
    qterms={w for w in re.findall(r"[a-z]{3,}|\d+(?:\.\d+)+|\d+",normalized) if w not in {"the","and","for","with","from","that","this","was","were","are","not","flight","passenger","airline"}}
    if not qterms:return 0.0
    dterms=set(re.findall(r"[a-z]{3,}|\d+(?:\.\d+)+|\d+",text))
    overlap=len(qterms & dterms)/len(qterms)
    # Clause lookup is a strong intent signal; retain clause punctuation exactly.
    clauses=re.findall(r"\b\d+(?:\.\d+)+\b",normalized)
    exact=1.0 if any(str(record.get("section", "")).strip().startswith(clause) for clause in clauses) else (0.5 if any(clause in text for clause in clauses) else 0.0)
    phrase=0.2 if any(phrase in normalized and phrase in text for phrase in ("alternate flight","meals and refreshments","extraordinary circumstances","same ticket")) else 0.0
    return min(1.0,overlap+exact+phrase)
@lru_cache(maxsize=2048)
def _retrieve_cached(query:str,top_k:int,index_mtime:float):
    vector=_EMBEDDER.encode([query])[0]; store=_store()
    candidates=store.search(vector,max(top_k*8,top_k))
    reranked=[]
    for item in candidates:
        lexical=_lexical_score(query,item)
        dense=float(item.get("score",0.0))
        item={**item,"dense_score":dense,"lexical_score":round(lexical,4),"score":round(0.45*dense+0.55*lexical,4)}
        reranked.append(item)
    reranked.sort(key=lambda p:p["score"],reverse=True)
    return tuple(reranked[:top_k])
def retrieve_passages(claim:str|dict[str,Any],top_k:int=5):
    if top_k<=0:return []
    if isinstance(claim,dict): query=str(claim.get("complaint",claim.get("text",""))) or " ".join(str(v) for v in claim.values() if v is not None)
    else: query=str(claim)
    query=query.strip()
    if not query:return []
    path=Path(os.getenv("RAG_INDEX_PATH","data/rag/faiss.index")); mtime=path.stat().st_mtime if path.exists() else 0.0
    matches=_retrieve_cached(query,top_k,mtime); output=[]
    for item in matches:
        source=str(item.get("source") or "Unknown source"); page=item.get("page"); section=item.get("section")
        location=f"page {page}" if page is not None else "page unknown"
        if section:location+=f", {section}"
        output.append({"text":item["text"],"citation":f"{source}, {location}","source":source,"page":page,"section":section})
    return output
def main():
    parser=argparse.ArgumentParser(description="Incrementally parse, chunk, embed and index the regulatory corpus")
    parser.add_argument("--incremental",action="store_true",help="add changed chunks and retire changed/removed sources")
    parser.add_argument("--rebuild",action="store_true",help="recreate the index from source PDFs")
    parser.add_argument("--reembed",action="store_true",help="re-embed active chunks using current runtime model settings")
    args=parser.parse_args()
    if not args.incremental and not args.rebuild and not args.reembed:parser.error("Specify --incremental, --rebuild, or --reembed")
    print(json.dumps({"active_chunks":rebuild_index(incremental=args.incremental and not args.rebuild,reembed=args.reembed)}))
if __name__=="__main__":main()
