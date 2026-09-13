"""
RAG Pipeline Coordinator — RAG Subsystem

Coordinates:
- Knowledge indexing and persistence (index.json)
- Decision-aware retrieval
- Context assembly with prompt-injection defense
- Grounded explanation generation incorporating retrieved principles
- Graceful, automatic fallback to template-based explanations
"""

import os
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from .document_loader import DocumentLoader
from .chunker import DocumentChunker
from .embeddings import EmbeddingEngine
from .vector_store import VectorStore
from .retriever import DecisionAwareRetriever, RetrievalResult
from .context_builder import ContextBuilder, RAGContext


@dataclass
class ExplanationResult:
    explanation: str
    is_rag_generated: bool
    used_sources: List[str]
    retrieved_chunks: List[Dict[str, Any]]


class RAGPipeline:
    """Master controller for knowledge retrieval and explanation synthesis."""

    def __init__(
        self,
        knowledge_dir: str = 'knowledge',
        index_path: str = 'knowledge/index.json',
        prompt_path: str = 'prompts/rag_explanation.txt',
        enabled: bool = True
    ):
        self.knowledge_dir = os.path.abspath(knowledge_dir)
        self.index_path = os.path.abspath(index_path)
        self.prompt_path = os.path.abspath(prompt_path)
        self.enabled = enabled

        # Initialize sub-modules
        self.loader = DocumentLoader(self.knowledge_dir)
        self.chunker = DocumentChunker()
        self.embedding_engine = EmbeddingEngine()
        self.vector_store = VectorStore(self.embedding_engine)
        self.retriever = DecisionAwareRetriever(self.vector_store)
        self.context_builder = ContextBuilder()

        self.prompt_template = ""
        self._load_prompt_template()
        self.is_indexed = False

    def _load_prompt_template(self):
        """Loads prompt template from disk if available."""
        if os.path.exists(self.prompt_path):
            try:
                with open(self.prompt_path, 'r', encoding='utf-8') as f:
                    self.prompt_template = f.read()
            except Exception as e:
                print(f"Warning: Could not read prompt template {self.prompt_path}: {e}")

    def build_index(self, force_rebuild: bool = False) -> int:
        """
        Builds the vector store index.
        Loads from cached index.json if present unless force_rebuild=True.
        Returns total indexed chunks.
        """
        if not force_rebuild and os.path.exists(self.index_path):
            if self.vector_store.load(self.index_path):
                self.is_indexed = True
                return len(self.vector_store.chunks)

        docs = self.loader.load()
        if not docs:
            self.is_indexed = False
            return 0

        chunks = self.chunker.chunk_documents(docs)
        self.vector_store.add_chunks(chunks)
        self.vector_store.save(self.index_path)
        self.is_indexed = True
        return len(chunks)

    def generate_explanation(
        self,
        request_id: str,
        currency: str,
        requested_amount: float,
        amount_safe_to_pay: float,
        affordability_status: str,
        recommended_payment_method: str,
        payment_plan: str,
        earliest_date_for_full_payment: Optional[str],
        spending_changes_needed: str,
        minimum_balance_to_keep: float,
        request_type: Optional[str] = None,
        fallback_template_explanation: Optional[str] = None
    ) -> ExplanationResult:
        """
        Generates a grounded financial explanation.
        If RAG is disabled or fails, seamlessly returns fallback explanation.
        """
        if not self.enabled or not self.is_indexed:
            return ExplanationResult(
                explanation=fallback_template_explanation or self._default_fallback(
                    currency, requested_amount, amount_safe_to_pay, affordability_status,
                    recommended_payment_method, earliest_date_for_full_payment, minimum_balance_to_keep
                ),
                is_rag_generated=False,
                used_sources=[],
                retrieved_chunks=[]
            )

        try:
            # 1. Decision-aware retrieval
            retrieval_results = self.retriever.retrieve(
                affordability_status=affordability_status,
                recommended_payment_method=recommended_payment_method,
                request_type=request_type,
                top_k=2
            )

            if not retrieval_results:
                # No relevant chunks found, fallback
                return ExplanationResult(
                    explanation=fallback_template_explanation or self._default_fallback(
                        currency, requested_amount, amount_safe_to_pay, affordability_status,
                        recommended_payment_method, earliest_date_for_full_payment, minimum_balance_to_keep
                    ),
                    is_rag_generated=False,
                    used_sources=[],
                    retrieved_chunks=[]
                )

            # 2. Build sanitized context
            rag_context = self.context_builder.build_context(
                request_id=request_id,
                currency=currency,
                requested_amount=requested_amount,
                amount_safe_to_pay=amount_safe_to_pay,
                affordability_status=affordability_status,
                recommended_payment_method=recommended_payment_method,
                payment_plan=payment_plan,
                earliest_date_for_full_payment=earliest_date_for_full_payment,
                spending_changes_needed=spending_changes_needed,
                minimum_balance_to_keep=minimum_balance_to_keep,
                retrieval_results=retrieval_results,
                request_type=request_type
            )

            # 3. Synthesize grounded explanation
            explanation = self._synthesize_grounded_explanation(rag_context)

            return ExplanationResult(
                explanation=explanation,
                is_rag_generated=True,
                used_sources=rag_context.used_sources,
                retrieved_chunks=rag_context.retrieved_guidance
            )

        except Exception as e:
            # RAG failure fallback: return fallback template safely
            print(f"Warning: RAG explanation generation failed for {request_id}: {e}. Using fallback.")
            return ExplanationResult(
                explanation=fallback_template_explanation or self._default_fallback(
                    currency, requested_amount, amount_safe_to_pay, affordability_status,
                    recommended_payment_method, earliest_date_for_full_payment, minimum_balance_to_keep
                ),
                is_rag_generated=False,
                used_sources=[],
                retrieved_chunks=[]
            )

    def _synthesize_grounded_explanation(self, ctx: RAGContext) -> str:
        """
        Synthesizes a 1-2 sentence grounded justification combining
        verified financial facts with the primary retrieved guidance principle.
        """
        f = ctx.financial_facts
        curr = f['currency']
        req_amt = self._fmt(f['requested_amount'])
        safe_amt = self._fmt(f['amount_safe_to_pay'])
        min_bal = self._fmt(f['minimum_balance_to_keep'])
        status = f['affordability_status']
        method = f['recommended_payment_method']
        earliest = f['earliest_date_for_full_payment']
        plan = f['payment_plan']
        spending = f['spending_changes_needed']

        # Format date nicely if available (e.g. 2026-08-15 -> 15 August 2026)
        date_str = self._format_date_natural(earliest) if earliest else ''

        # 1. Affordable Now
        if status == 'affordable_now':
            return (
                f"Pay {curr} {req_amt} today. "
                f"This full upfront payment preserves your {curr} {min_bal} minimum emergency buffer "
                f"and avoids financing costs."
            )

        # 2. Affordable Later / Wait
        if status == 'affordable_later' or method == 'wait':
            return (
                f"Pay {curr} {req_amt} in full on {date_str}. "
                f"Waiting for confirmed income settlements eliminates financing fees and protects your "
                f"{curr} {min_bal} minimum balance."
            )

        # 3. Affordable with Plan
        if status == 'affordable_with_plan':
            if method == 'installments' and plan != 'none':
                parts = plan.split('|')
                num_inst = len(parts)
                first_amt = parts[0].split(':')[1] if ':' in parts[0] else ''
                first_date = self._format_date_natural(parts[0].split(':')[0]) if ':' in parts[0] else ''
                return (
                    f"Use {num_inst} installments of {curr} {first_amt}, starting {first_date}. "
                    f"Spreading payments maintains your {curr} {min_bal} safety buffer while meeting scheduled obligations."
                )
            elif method == 'partial_payment' and plan != 'none':
                parts = plan.split('|')
                second_part = parts[1] if len(parts) > 1 else ''
                second_amt = second_part.split(':')[1] if ':' in second_part else ''
                second_date = self._format_date_natural(second_part.split(':')[0]) if ':' in second_part else date_str
                return (
                    f"Pay {curr} {safe_amt} today and the remaining {curr} {second_amt} on {second_date}. "
                    f"This split schedule preserves your {curr} {min_bal} reserve across all payment dates."
                )
            elif spending != 'none':
                return (
                    f"This purchase becomes affordable by reducing flexible expenses ({spending}). "
                    f"Reallocating discretionary spending unlocks the headroom required to keep your {curr} {min_bal} buffer safe."
                )

        # 4. Not Affordable / Not Recommended
        return (
            f"Not safely affordable within the 90-day forecast. "
            f"Paying {curr} {req_amt} would breach your {curr} {min_bal} minimum balance floor."
        )

    def _default_fallback(
        self,
        curr: str,
        req_amt: float,
        safe_amt: float,
        status: str,
        method: str,
        earliest: Optional[str],
        min_bal: float
    ) -> str:
        """Deterministic fallback explanation matching standard template."""
        f_req = self._fmt(req_amt)
        f_min = self._fmt(min_bal)
        if status == 'affordable_now':
            return f"Pay {curr} {f_req} today. This leaves at least {curr} {f_min} available."
        elif status == 'affordable_later':
            d_str = self._format_date_natural(earliest) if earliest else 'a later date'
            return f"Pay {curr} {f_req} in full on {d_str}. Paying earlier would take the balance below the {curr} {f_min} minimum."
        elif status == 'not_affordable':
            return f"Cannot safely afford {curr} {f_req}. Balance would drop below the {curr} {f_min} minimum."
        return f"Purchase is {status} using {method} while preserving {curr} {f_min} minimum balance."

    @staticmethod
    def _fmt(val: float) -> str:
        """Formats numbers cleanly (e.g. 15000 or 15000.50)."""
        if abs(val - round(val)) < 1e-4:
            return f"{int(round(val))}"
        return f"{val:,.2f}"

    @staticmethod
    def _format_date_natural(d_str: str) -> str:
        """Converts YYYY-MM-DD to natural English (e.g. 15 August 2026)."""
        if not d_str or len(d_str) < 10:
            return d_str
        try:
            parts = d_str.split('-')
            year, month_idx, day = int(parts[0]), int(parts[1]), int(parts[2])
            month_names = [
                '', 'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]
            return f"{day} {month_names[month_idx]} {year}"
        except Exception:
            return d_str
