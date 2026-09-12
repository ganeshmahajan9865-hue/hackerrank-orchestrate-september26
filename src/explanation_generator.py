"""
Explanation Generator Module

Generates concise, factual 2-sentence justifications grounded strictly in computed facts.
Ensures 100% factual accuracy, correct currency, amounts, dates, and decision reasoning.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import Dict, List, Optional, Any
import datetime
import pandas as pd

from src.data_joiner import RequestContext
from src.decision_engine import DecisionResult
from src.payment_plans import format_amount


class ExplanationGenerator:
    """Generates grounded natural-language explanations for financial recommendations."""

    def __init__(self):
        pass

    def _format_date(self, date_str: str) -> str:
        """Formats YYYY-MM-DD into human readable date, e.g. 8 August 2025."""
        try:
            dt = datetime.date.fromisoformat(date_str)
            # e.g. 8 August 2025
            return f"{dt.day} {dt.strftime('%B')} {dt.year}"
        except Exception:
            return date_str

    def _format_changes_text(self, ctx: RequestContext, changes_needed: str) -> str:
        """Constructs natural language phrase for spending changes."""
        if not changes_needed or changes_needed == 'none':
            return ""

        parts = changes_needed.split('|')
        action_phrases = []
        ev_map = {str(r['event_id']): r for _, r in ctx.events.iterrows()}

        for p in parts:
            tokens = p.split(':')
            act = tokens[0]
            ev_id = tokens[1]
            desc = "the subscription"
            if ev_id in ev_map:
                desc = str(ev_map[ev_id]['description']).lower()

            if act == 'stop':
                action_phrases.append(f"Stop the {desc}")
            elif act == 'reduce_to':
                new_amt = tokens[2] if len(tokens) > 2 else ""
                action_phrases.append(f"Reduce the {desc} to {ctx.profile.home_currency} {new_amt}")

        if len(action_phrases) == 1:
            return action_phrases[0]
        elif len(action_phrases) == 2:
            return f"{action_phrases[0]} and {action_phrases[1].lower()}"
        else:
            return "; ".join(action_phrases)

    def generate(self, ctx: RequestContext, result: DecisionResult) -> str:
        """Generates grounded explanation based on decision facts."""
        curr = ctx.profile.home_currency
        req_amt = ctx.requested_amount
        min_bal = ctx.profile.minimum_balance_to_keep
        status = result.affordability_status
        method = result.recommended_payment_method
        plan = result.chosen_plan
        safe_amt = result.amount_safe_to_pay
        earliest = result.earliest_date_for_full_payment
        deadline = ctx.desired_completion_date

        if status == 'affordable_now':
            return (
                f"Pay {curr} {format_amount(req_amt)} today. "
                f"This leaves at least {curr} {format_amount(min_bal)} available over the next 90 days."
            )

        elif status == 'affordable_with_plan':
            if method == 'installments':
                num = plan.number_of_payments
                inst_amt = plan.payments[0][1] if plan.payments else (req_amt / num)
                first_date = plan.payments[0][0] if plan.payments else ctx.request_date
                human_first = self._format_date(first_date)
                return (
                    f"Use {num} installments of {curr} {format_amount(inst_amt)}, starting {human_first}. "
                    f"This leaves at least {curr} {format_amount(min_bal)} available."
                )

            elif method == 'partial_payment':
                p1_amt = plan.payments[0][1] if len(plan.payments) > 0 else safe_amt
                p2_amt = plan.payments[1][1] if len(plan.payments) > 1 else (req_amt - safe_amt)
                p2_date = plan.payments[1][0] if len(plan.payments) > 1 else earliest
                human_p2 = self._format_date(p2_date) if p2_date else ""
                return (
                    f"Pay {curr} {format_amount(p1_amt)} today and the remaining {curr} {format_amount(p2_amt)} on {human_p2}. "
                    f"This completes the full request and keeps the {curr} {format_amount(min_bal)} minimum protected."
                )

            elif method == 'full_payment':
                changes_phrase = self._format_changes_text(ctx, result.spending_changes_needed)
                if not changes_phrase:
                    changes_phrase = "Adjust flexible expenses"
                return (
                    f"{changes_phrase}, then pay {curr} {format_amount(req_amt)} today. "
                    f"This leaves at least {curr} {format_amount(min_bal)} available."
                )

        elif status == 'affordable_later':
            human_earliest = self._format_date(earliest) if earliest else "the projected date"
            return (
                f"Pay {curr} {format_amount(req_amt)} in full on {human_earliest}. "
                f"Paying earlier would take the balance below the {curr} {format_amount(min_bal)} minimum."
            )

        else: # not_affordable
            if safe_amt > 0 and (not earliest or pd.isna(earliest)):
                return (
                    f"Do not proceed with the {curr} {format_amount(req_amt)} request. "
                    f"Although {curr} {format_amount(safe_amt)} is available today, the full amount cannot be completed safely within 90 days."
                )
            human_deadline = self._format_date(deadline) if deadline else "the desired date"
            return (
                f"Do not make this payment by {human_deadline}. "
                f"None of the available options keeps the {curr} {format_amount(min_bal)} minimum protected."
            )
