"""
Embedding Engine Module — RAG Subsystem

Generates normalized vector representations for text chunks and queries.
Uses an offline-first, high-performance TF-IDF vectorizer with sublinear term weighting
and L2-normalization, ensuring deterministic, zero-dependency execution.
"""

from typing import List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


class EmbeddingEngine:
    """Computes normalized vector representations for documents and search queries."""

    def __init__(self, max_features: int = 1000):
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            ngram_range=(1, 2),
            sublinear_tf=True,
            max_features=max_features,
            norm='l2'
        )
        self.is_fitted = False
        self.dimension = 0

    def fit(self, texts: List[str]) -> 'EmbeddingEngine':
        """Fits vocabulary and IDF weights on the corpus."""
        if not texts:
            return self
        self.vectorizer.fit(texts)
        self.is_fitted = True
        self.dimension = len(self.vectorizer.get_feature_names_out())
        return self

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        """Transforms a list of texts into normalized embedding vectors."""
        if not self.is_fitted:
            self.fit(texts)
        
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        matrix = self.vectorizer.transform(texts)
        return matrix.toarray().astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Transforms a single query string into a 1D normalized embedding vector."""
        if not self.is_fitted:
            raise ValueError("EmbeddingEngine must be fitted before embedding queries.")
        
        matrix = self.vectorizer.transform([query])
        return matrix.toarray()[0].astype(np.float32)
