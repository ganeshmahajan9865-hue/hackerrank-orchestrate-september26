"""
Context Builder Module — RAG Subsystem

Builds strict, tamper-proof context payloads containing verified financial facts
and retrieved supporting guidance chunks. Sanitizes untrusted strings against injection.
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .retriever import RetrievalResult


@dataclass
class RAGContext:
    financial_facts: Dict[str, Any]
    retrieved_guidance: List[Dict[str, Any]]
    used_sources: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.financial_facts,
            'retrieved_guidance': self.retrieved_guidance,
            'used_sources': self.used_sources
        }


class ContextBuilder:
    """Combines deterministic financial facts with retrieved guidance into a safe payload."""

    INJECTION_PATTERNS = [
        re.compile(r'ignore (all )?previous instructions', re.IGNORECASE),
        re.compile(r'system prompt', re.IGNORECASE),
        re.compile(r'override (the )?decision', re.IGNORECASE),
        re.compile(r'approve (this )?immediately', re.IGNORECASE),
        re.compile(r'you are now in developer mode', re.IGNORECASE),
        re.compile(r'disregard (the )?financial', re.IGNORECASE)
    ]

    def sanitize_text(self, text: str) -> str:
        """Neutralizes adversarial directives in untrusted text fields."""
        sanitized = text
        for pattern in self.INJECTION_PATTERNS:
            sanitized = pattern.sub('[REDACTED ADVERSARIAL DIRECTIVE]', sanitized)
        return sanitized.strip()

    def build_context(
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
        retrieval_results: List[RetrievalResult],
        request_type: Optional[str] = None
    ) -> RAGContext:
        """Constructs safe payload for the explanation generator."""
        financial_facts = {
            'request_id': str(request_id),
            'currency': str(currency),
            'requested_amount': round(float(requested_amount), 2),
            'amount_safe_to_pay': round(float(amount_safe_to_pay), 2),
            'affordability_status': str(affordability_status),
            'recommended_payment_method': str(recommended_payment_method),
            'payment_plan': str(payment_plan),
            'earliest_date_for_full_payment': str(earliest_date_for_full_payment or ''),
            'spending_changes_needed': str(spending_changes_needed),
            'minimum_balance_to_keep': round(float(minimum_balance_to_keep), 2),
            'request_type': self.sanitize_text(str(request_type or ''))
        }

        guidance_items = []
        used_sources = []

        for res in retrieval_results:
            clean_text = self.sanitize_text(res.chunk.text)
            guidance_items.append({
                'source': res.source,
                'chunk_id': res.chunk_id,
                'topic': res.topic,
                'section': res.chunk.section,
                'relevance_score': round(res.score, 4),
                'text': clean_text
            })
            if res.source not in used_sources:
                used_sources.append(res.source)

        return RAGContext(
            financial_facts=financial_facts,
            retrieved_guidance=guidance_items,
            used_sources=used_sources
        )
