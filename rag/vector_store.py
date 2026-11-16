"""Appendable FAISS index with an active metadata sidecar and corpus manifest."""
from __future__ import annotations
import json,hashlib
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
class FaissVectorStore:
    def __init__(self,index_path:str|Path="data/rag/faiss.index"):
        self.index_path=Path(index_path); self.metadata_path=self.index_path.with_suffix(".json"); self._index=None; self._records=[]; self.manifest={}
    def build(self,vectors:Any,records:list[dict[str,Any]]):
        import faiss,numpy as np
        matrix=np.asarray(vectors,dtype="float32")
        if matrix.ndim!=2 or len(matrix)!=len(records): raise ValueError("one vector required per record")
        if not len(records): raise ValueError("Cannot build index without chunks")
        faiss.normalize_L2(matrix); self._index=faiss.IndexFlatIP(matrix.shape[1]); self._index.add(matrix); self._records=[dict(r,active=True) for r in records]
    def known_chunk_ids(self): return {str(r.get("chunk_id")) for r in self._records}
    def active_records(self): return [r for r in self._records if r.get("active",True)]
    def append_incremental(self,vectors:Any,records:list[dict[str,Any]]):
        import faiss,numpy as np
        if self._index is None and self.index_path.exists(): self.load()
        matrix=np.asarray(vectors,dtype="float32")
        if matrix.size==0: return
        if matrix.ndim!=2 or len(matrix)!=len(records): raise ValueError("one vector required per record")
        if self._index is None:
            faiss.normalize_L2(matrix); self._index=faiss.IndexFlatIP(matrix.shape[1]); self._index.add(matrix); self._records=[dict(r,active=True) for r in records]; return
        if matrix.shape[1]!=self._index.d: raise ValueError("Embedding dimension changed; use --reembed")
        incoming={str(r.get("source_path",r.get("source"))):str(r.get("document_version","")) for r in records}
        ids={str(r.get("chunk_id")) for r in records}
        for old in self._records:
            source=str(old.get("source_path",old.get("source")))
            if source in incoming and str(old.get("document_version",""))!=incoming[source]: old["active"]=False
        known=self.known_chunk_ids(); pairs=[r for r in records if str(r.get("chunk_id")) not in known]
        if not pairs: return
        vec=np.asarray(vectors,dtype="float32")
        if len(vec)!=len(records): raise ValueError("vectors must align with incoming records")
        indices=[i for i,r in enumerate(records) if str(r.get("chunk_id")) not in known]
        vec=vec[indices]; faiss.normalize_L2(vec); self._index.add(vec); self._records.extend(dict(r,active=True) for r in pairs)
    def set_manifest(self,**values): self.manifest.update(values)
    def save(self):
        if self._index is None: raise RuntimeError("Build or load index before saving")
        import faiss
        self.index_path.parent.mkdir(parents=True,exist_ok=True); faiss.write_index(self._index,str(self.index_path))
        self.manifest.update({"built_at":datetime.now(timezone.utc).isoformat(),"active_chunks":len(self.active_records()),"indexed_vectors":len(self._records)})
        self.metadata_path.write_text(json.dumps({"records":self._records,"manifest":self.manifest},ensure_ascii=False,indent=2),encoding="utf-8")
    def load(self):
        import faiss
        if not self.index_path.exists() or not self.metadata_path.exists(): raise FileNotFoundError(f"Index not found at {self.index_path}; run python -m rag.retrieval --incremental")
        self._index=faiss.read_index(str(self.index_path)); raw=json.loads(self.metadata_path.read_text(encoding="utf-8"))
        if isinstance(raw,list): self._records=raw; self.manifest={}
        else: self._records=raw.get("records",[]); self.manifest=raw.get("manifest",{})
        if self._index.ntotal!=len(self._records): raise ValueError("FAISS and metadata vector counts do not match")
    def search(self,query_vector:Any,top_k:int=5):
        if top_k<=0:return []
        if self._index is None:self.load()
        import numpy as np,faiss
        query=np.asarray(query_vector,dtype="float32").reshape(1,-1); faiss.normalize_L2(query)
        scores,indices=self._index.search(query,min(max(top_k*4,top_k),self._index.ntotal)); result=[]
        for score,index in zip(scores[0],indices[0]):
            if index<0: continue
            record=self._records[int(index)]
            if record.get("active",True): result.append({**record,"score":float(score)})
            if len(result)>=top_k:break
        return result
