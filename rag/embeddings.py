"""Local embeddings: injected Sentence Transformers model or deterministic hashing fallback."""
from __future__ import annotations
import hashlib, os, re
from functools import lru_cache
from typing import Any
import numpy as np

class SentenceTransformerEmbedder:
    """Use a runtime-selected local model; hash embeddings keep clean-clone demo offline."""
    DIMENSION = 384
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name if model_name is not None else os.getenv("RAG_EMBEDDING_MODEL", "")
        self._model: Any = None
    def _get_model(self):
        if not self.model_name: return None
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError("Local sentence embedding support requires sentence-transformers") from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model
    @classmethod
    @lru_cache(maxsize=10000)
    def _hash_one(cls, text: str):
        vector = np.zeros(cls.DIMENSION, dtype="float32")
        for token in re.findall(r"[\w]+", text.lower()):
            digest=hashlib.blake2b(token.encode("utf-8"),digest_size=8).digest()
            value=int.from_bytes(digest,"little"); index=value % cls.DIMENSION
            vector[index] += 1.0 if (value >> 16) & 1 else -1.0
        norm=float(np.linalg.norm(vector))
        if norm: vector /= norm
        return vector
    def encode(self, texts: list[str]):
        if not texts: return np.empty((0,self.DIMENSION),dtype="float32")
        model=self._get_model()
        if model is None: return np.stack([self._hash_one(str(text)) for text in texts])
        return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
