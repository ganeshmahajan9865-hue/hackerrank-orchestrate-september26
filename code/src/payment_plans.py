"""
Payment Plans Module

Defines and constructs candidate payment plans:
- full_payment
- installments
- partial_payment
- wait
- not_recommended
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import datetime
import pandas as pd

from src.data_joiner import RequestContext


def format_amount(amt: float) -> str:
    """Formats amounts cleanly: integer string if whole number, else 2 decimal places."""
    if abs(amt - round(amt)) < 1e-4:
        return str(int(round(amt)))
    return f"{amt:.2f}"


@dataclass
class CandidatePlan:
    plan_type: str  # 'full_payment', 'installments', 'partial_payment', 'wait', 'not_recommended'
    payment_option_id: Optional[str]
    payments: List[Tuple[str, float]]
    total_cost: float
    start_date: str
    completion_date: str
    number_of_payments: int
    spending_changes: List[str] = field(default_factory=list)
    formatted_plan: str = 'none'

    def is_within_deadline(self, desired_completion_date: str) -> bool:
        if not self.completion_date or self.completion_date == '9999-12-31':
            return False
        return self.completion_date <= desired_completion_date


class PaymentPlanEngine:
    """Generates valid candidate plans from user context and seller payment options."""

    def __init__(self):
        pass

    def build_full_payment_plan(
        self,
        ctx: RequestContext,
        spending_changes: Optional[List[str]] = None
    ) -> CandidatePlan:
        """Builds immediate full payment plan on request_date."""
        req_date = ctx.request_date
        amt = ctx.requested_amount
        changes = spending_changes or []
        formatted = f"{req_date}:{format_amount(amt)}"

        return CandidatePlan(
            plan_type='full_payment',
            payment_option_id=None,
            payments=[(req_date, amt)],
            total_cost=amt,
            start_date=req_date,
            completion_date=req_date,
            number_of_payments=1,
            spending_changes=changes,
            formatted_plan=formatted
        )

    def build_installment_plans(
        self,
        ctx: RequestContext,
        spending_changes: Optional[List[str]] = None
    ) -> List[CandidatePlan]:
        """Builds installment plans from request_payment_options.csv matching user preferences."""
        changes = spending_changes or []
        plans = []

        allowed_methods = ctx.profile.payment_methods_user_will_consider
        if 'installments' not in allowed_methods:
            return plans

        max_months = ctx.profile.max_installment_months

        opts = ctx.payment_options
        inst_opts = opts[opts['payment_method'] == 'installments']

        for _, row in inst_opts.iterrows():
            opt_id = str(row['payment_option_id'])
            num_payments = int(row['number_of_payments'])
            freq_days = int(row['payment_frequency_days'])
            pmt_amt = float(row['payment_amount'])
            tot_cost = float(row['total_payable_amount'])
            first_date_str = str(row['first_payment_date'])

            # Check max_installment_months constraint
            if pd.notna(max_months) and num_payments > max_months:
                continue

            # Build payments schedule
            first_date = datetime.date.fromisoformat(first_date_str)
            payments = []
            for k in range(num_payments):
                p_date = first_date + datetime.timedelta(days=k * freq_days)
                payments.append((p_date.strftime('%Y-%m-%d'), pmt_amt))

            formatted = '|'.join(f"{d}:{format_amount(a)}" for d, a in payments)

            plans.append(CandidatePlan(
                plan_type='installments',
                payment_option_id=opt_id,
                payments=payments,
                total_cost=tot_cost,
                start_date=payments[0][0],
                completion_date=payments[-1][0],
                number_of_payments=num_payments,
                spending_changes=changes,
                formatted_plan=formatted
            ))

        return plans

    def build_partial_payment_plan(
        self,
        ctx: RequestContext,
        amount_safe_to_pay: float,
        earliest_date_for_full: Optional[str],
        spending_changes: Optional[List[str]] = None
    ) -> Optional[CandidatePlan]:
        """
        Builds partial payment plan (exactly 2 payments: today safe amount, then remainder).
        Valid only if:
        - request allows partial payment
        - user considers partial payment
        - 0 < amount_safe_to_pay < requested_amount
        """
        changes = spending_changes or []
        allows_partial = ctx.allows_partial_payment
        if isinstance(allows_partial, str):
            allows_partial = (allows_partial.lower() == 'true')

        if not allows_partial:
            return None

        allowed_methods = ctx.profile.payment_methods_user_will_consider
        if 'partial_payment' not in allowed_methods:
            return None

        req_amt = ctx.requested_amount
        if not (0 < amount_safe_to_pay < req_amt):
            return None

        if not earliest_date_for_full:
            return None

        if earliest_date_for_full > ctx.desired_completion_date:
            return None

        remainder = req_amt - amount_safe_to_pay
        payments = [
            (ctx.request_date, amount_safe_to_pay),
            (earliest_date_for_full, remainder)
        ]

        formatted = f"{ctx.request_date}:{format_amount(amount_safe_to_pay)}|{earliest_date_for_full}:{format_amount(remainder)}"

        return CandidatePlan(
            plan_type='partial_payment',
            payment_option_id=None,
            payments=payments,
            total_cost=req_amt,
            start_date=ctx.request_date,
            completion_date=earliest_date_for_full,
            number_of_payments=2,
            spending_changes=changes,
            formatted_plan=formatted
        )

    def build_wait_plan(
        self,
        ctx: RequestContext,
        earliest_date_for_full: Optional[str]
    ) -> Optional[CandidatePlan]:
        """Builds single future full payment on earliest_date_for_full_payment."""
        if not earliest_date_for_full:
            return None

        allowed_methods = ctx.profile.payment_methods_user_will_consider
        if 'full_payment' not in allowed_methods:
            return None

        req_amt = ctx.requested_amount
        formatted = f"{earliest_date_for_full}:{format_amount(req_amt)}"

        return CandidatePlan(
            plan_type='wait',
            payment_option_id=None,
            payments=[(earliest_date_for_full, req_amt)],
            total_cost=req_amt,
            start_date=earliest_date_for_full,
            completion_date=earliest_date_for_full,
            number_of_payments=1,
            spending_changes=[],
            formatted_plan=formatted
        )

    def build_not_recommended_plan(self) -> CandidatePlan:
        """Fallback when no safe plan exists."""
        return CandidatePlan(
            plan_type='not_recommended',
            payment_option_id=None,
            payments=[],
            total_cost=0.0,
            start_date='',
            completion_date='',
            number_of_payments=0,
            spending_changes=[],
            formatted_plan='none'
        )
