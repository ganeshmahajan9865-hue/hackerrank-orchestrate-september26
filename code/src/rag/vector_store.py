"""
Vector Store Module — RAG Subsystem

Provides in-memory vector indexing and search with cosine similarity,
metadata filtering, and persistent disk serialization (JSON).
"""

import json
import os
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from .chunker import DocumentChunk
from .embeddings import EmbeddingEngine


class VectorStore:
    """Stores chunk vectors and performs metadata-aware cosine similarity search."""

    def __init__(self, embedding_engine: Optional[EmbeddingEngine] = None):
        self.embedding_engine = embedding_engine or EmbeddingEngine()
        self.chunks: List[DocumentChunk] = []
        self.vectors: Optional[np.ndarray] = None

    def add_chunks(self, chunks: List[DocumentChunk]):
        """Indexes chunks and builds normalized vector matrix."""
        if not chunks:
            self.chunks = []
            self.vectors = np.empty((0, 0), dtype=np.float32)
            return

        self.chunks = chunks
        texts = [f"{c.topic} {c.section} {c.text}" for c in chunks]
        
        # Fit and embed
        self.embedding_engine.fit(texts)
        self.vectors = self.embedding_engine.embed_documents(texts)

    def search(
        self,
        query: str,
        top_k: int = 3,
        topic_filter: Optional[List[str]] = None,
        min_score: float = 0.05
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Searches for top_k most similar chunks matching query.
        Optionally restricts candidates by topic.
        Returns list of (chunk, similarity_score).
        """
        if not self.chunks or self.vectors is None or len(self.vectors) == 0:
            return []

        query_vec = self.embedding_engine.embed_query(query)
        if np.linalg.norm(query_vec) == 0:
            return []

        # Cosine similarity (vectors are L2 normalized)
        scores = np.dot(self.vectors, query_vec)

        # Apply topic filter and score threshold
        results = []
        for idx, score in enumerate(scores):
            chunk = self.chunks[idx]
            if topic_filter and chunk.topic not in topic_filter:
                continue
            if score >= min_score:
                results.append((chunk, float(score)))

        # Sort descending by score
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def save(self, index_path: str = 'knowledge/index.json'):
        """Serializes vector store and chunks to disk."""
        os.makedirs(os.path.dirname(os.path.abspath(index_path)), exist_ok=True)
        data = {
            'chunks': [
                {
                    'chunk_id': c.chunk_id,
                    'source': c.source,
                    'topic': c.topic,
                    'section': c.section,
                    'text': c.text,
                    'metadata': c.metadata
                }
                for c in self.chunks
            ]
        }
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load(self, index_path: str = 'knowledge/index.json') -> bool:
        """Loads and re-indexes chunks from serialized index file."""
        if not os.path.exists(index_path):
            return False

        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            chunks = [
                DocumentChunk(
                    chunk_id=item['chunk_id'],
                    source=item['source'],
                    topic=item['topic'],
                    section=item['section'],
                    text=item['text'],
                    metadata=item.get('metadata', {})
                )
                for item in data.get('chunks', [])
            ]
            self.add_chunks(chunks)
            return True
        except Exception as e:
            print(f"Warning: Failed to load vector index from {index_path}: {e}")
            return False
