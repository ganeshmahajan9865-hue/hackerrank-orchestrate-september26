"""
RAG Subsystem for Financial Affordability System

Provides modular document loading, chunking, embedding, vector search,
decision-aware retrieval, context assembly, and grounded explanation generation.
"""

from .document_loader import Document, DocumentLoader
from .chunker import DocumentChunk, DocumentChunker
from .embeddings import EmbeddingEngine
from .vector_store import VectorStore
from .retriever import DecisionAwareRetriever, RetrievalResult
from .context_builder import ContextBuilder, RAGContext
from .rag_pipeline import RAGPipeline

__all__ = [
    'Document',
    'DocumentLoader',
    'DocumentChunk',
    'DocumentChunker',
    'EmbeddingEngine',
    'VectorStore',
    'DecisionAwareRetriever',
    'RetrievalResult',
    'ContextBuilder',
    'RAGContext',
    'RAGPipeline',
]
