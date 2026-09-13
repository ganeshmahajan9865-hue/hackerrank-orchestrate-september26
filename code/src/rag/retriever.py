"""
Decision-Aware Retriever Module — RAG Subsystem

Routes queries and topic scopes based on the computed financial decision:
- affordable_now -> budgeting + full payment + safe spending
- affordable_with_plan -> installment + payment plan terms + spending reduction
- affordable_later -> delayed purchase + emergency buffer + cash forecasting
- not_affordable -> risk mitigation + emergency buffer + discretionary spending
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .vector_store import VectorStore
from .chunker import DocumentChunk


@dataclass
class RetrievalResult:
    chunk: DocumentChunk
    score: float
    source: str
    chunk_id: str
    topic: str


class DecisionAwareRetriever:
    """Retrieves relevant financial knowledge aligned with computed decision states."""

    # Map affordability status to prioritized topic categories and semantic search keywords
    DECISION_ROUTING = {
        'affordable_now': {
            'topics': ['affordability', 'payment_methods', 'budgeting'],
            'query': 'affordable now safe to pay full upfront payment emergency buffer cash flow'
        },
        'affordable_with_plan': {
            'topics': ['payment_methods', 'spending', 'financial_terms'],
            'query': 'installment payments payment plan partial payment schedule reducing flexible expenses'
        },
        'affordable_later': {
            'topics': ['affordability', 'emergency_fund', 'budgeting'],
            'query': 'delayed purchases wait strategy confirmed salary timing minimum balance buffer'
        },
        'not_affordable': {
            'topics': ['affordability', 'emergency_fund', 'spending'],
            'query': 'not affordable financial risk opportunity cost emergency buffer discretionary spending'
        }
    }

    # Additional method-specific search enhancements
    METHOD_ENHANCEMENTS = {
        'full_payment': 'full payment benefits zero interest immediate settlement',
        'installments': 'installments multi-month financing payment obligation',
        'partial_payment': 'partial payment split two payments completion date',
        'wait': 'wait strategy confirmed future salary settlement date',
        'not_recommended': 'not recommended risk of overdraft breach minimum balance floor'
    }

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def retrieve(
        self,
        affordability_status: str,
        recommended_payment_method: str,
        request_type: Optional[str] = None,
        top_k: int = 2
    ) -> List[RetrievalResult]:
        """
        Executes decision-guided semantic retrieval.
        Returns top-k ranked knowledge chunks with provenance metadata.
        """
        routing = self.DECISION_ROUTING.get(
            affordability_status,
            {
                'topics': ['affordability', 'budgeting'],
                'query': 'financial affordability safe spending minimum balance'
            }
        )

        query_parts = [routing['query']]
        
        # Add method-specific keyword boost
        if recommended_payment_method in self.METHOD_ENHANCEMENTS:
            query_parts.append(self.METHOD_ENHANCEMENTS[recommended_payment_method])

        # Add request type context if available
        if request_type and request_type.lower() != 'nan':
            query_parts.append(f"{request_type} expense priority")

        combined_query = " ".join(query_parts)
        topic_filter = routing['topics']

        raw_results = self.vector_store.search(
            query=combined_query,
            top_k=top_k,
            topic_filter=topic_filter,
            min_score=0.03
        )

        # Fallback to unrestricted search if topic-restricted returned nothing
        if not raw_results:
            raw_results = self.vector_store.search(
                query=combined_query,
                top_k=top_k,
                topic_filter=None,
                min_score=0.01
            )

        retrieval_results = [
            RetrievalResult(
                chunk=chunk,
                score=score,
                source=chunk.source,
                chunk_id=chunk.chunk_id,
                topic=chunk.topic
            )
            for chunk, score in raw_results
        ]

        return retrieval_results
