"""
Forecast Engine Module

Simulates daily cash flow for 90 days from request_date.
Evaluates plan feasibility, safe payment headroom, and earliest full-payment date.
Strictly deterministic Python calculations — no LLM arithmetic.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set, Any
import datetime
import calendar
import pandas as pd
import numpy as np

from src.data_joiner import RequestContext


@dataclass
class SimulationResult:
    is_safe: bool
    min_balance_observed: float
    min_headroom: float
    breach_date: Optional[str]
    daily_balances: Dict[str, float]


class ForecastEngine:
    """90-day daily cash balance simulator and headroom calculator."""

    def __init__(self, forecast_days: int = 90, conservative_buffer: float = 1.15):
        self.forecast_days = forecast_days
        self.conservative_buffer = conservative_buffer

    def build_daily_deltas(
        self,
        ctx: RequestContext,
        recon: Dict[str, Any],
        spending_stops: Optional[Set[str]] = None,
        spending_reduces: Optional[Dict[str, float]] = None
    ) -> Dict[datetime.date, float]:
        """Projects daily income (+) and expense (-) cash flow changes over the forecast window."""
        spending_stops = spending_stops or set()
        spending_reduces = spending_reduces or {}

        req_date = datetime.date.fromisoformat(ctx.request_date)
        end_date = req_date + datetime.timedelta(days=self.forecast_days)
        total_days = (end_date - req_date).days + 1

        daily_deltas: Dict[datetime.date, float] = {
            req_date + datetime.timedelta(days=i): 0.0 for i in range(total_days)
        }

        # 1. Apply explicit future events in dataset (pending debits, scheduled items)
        for e in recon['processed_events']:
            e_date = datetime.date.fromisoformat(e.date)
            if req_date <= e_date <= end_date:
                amt = e.amount
                if e.event_id in spending_stops:
                    continue
                if e.event_id in spending_reduces:
                    amt = spending_reduces[e.event_id]

                if e.direction == 'debit' and e.status in ('pending', 'scheduled'):
                    daily_deltas[e_date] -= amt
                elif e.direction == 'credit' and e.status == 'scheduled':
                    # Apply salary message update if available
                    for u in recon['message_updates']:
                        if u.new_amount and ('salary' in u.action_type or e.category in ('salary', 'income')):
                            amt = u.new_amount
                    daily_deltas[e_date] += amt

        # 2. Project recurring monthly salary
        salary_events = [
            e for e in recon['processed_events']
            if e.direction == 'credit' and e.category in ('salary', 'income') and e.status in ('settled', 'scheduled')
        ]
        if salary_events:
            sal_days = [pd.to_datetime(e.date).day for e in salary_events]
            sal_day = int(np.median(sal_days))
            sal_amts = [e.amount for e in salary_events if e.amount > 0]
            sal_amt = float(np.median(sal_amts)) if sal_amts else 0.0

            # Check message updates for salary
            for u in recon['message_updates']:
                if u.new_amount and 'salary' in u.action_type:
                    sal_amt = u.new_amount
                if u.new_date and 'salary' in u.action_type:
                    sal_day = pd.to_datetime(u.new_date).day

            for dt in daily_deltas:
                max_days = calendar.monthrange(dt.year, dt.month)[1]
                effective_sal_day = min(sal_day, max_days)
                if dt.day == effective_sal_day and dt >= req_date:
                    # Don't duplicate if already an explicit scheduled credit on this day
                    has_explicit = any(
                        datetime.date.fromisoformat(e.date) == dt and e.direction == 'credit' and e.category in ('salary', 'income')
                        for e in recon['processed_events'] if e.status == 'scheduled'
                    )
                    if not has_explicit:
                        daily_deltas[dt] += sal_amt

        # 3. Project recurring commitments
        for c in recon['recurring_commitments']:
            amt = c.amount
            if c.sample_event_id in spending_stops:
                continue
            if c.sample_event_id in spending_reduces:
                amt = spending_reduces[c.sample_event_id]

            for dt in daily_deltas:
                if dt.day == c.day_of_month and dt >= req_date:
                    # Check if already paid in current month
                    if dt.year == req_date.year and dt.month == req_date.month:
                        if c.last_event_date and c.last_event_date[:7] == ctx.request_date[:7]:
                            continue

                    has_explicit = any(
                        datetime.date.fromisoformat(e.date) == dt and e.category == c.category
                        for e in recon['processed_events'] if e.status in ('pending', 'scheduled')
                    )
                    if not has_explicit:
                        daily_deltas[dt] -= amt

        # 4. Conservative essential variable spending (groceries, transport, protected)
        evs = ctx.events
        settled_debits = evs[(evs['direction'] == 'debit') & (evs['status'] == 'settled') & (evs['event_date'] <= ctx.request_date)]
        essential_cats = {'groceries', 'transport'}
        prot = set(ctx.profile.expense_categories_to_protect or [])
        essential_cats.update(prot.intersection({'dining', 'shopping', 'healthcare', 'entertainment'}))

        ess_debits = settled_debits[settled_debits['category'].isin(essential_cats)]
        if len(ess_debits) > 0 and len(settled_debits) > 0:
            min_d = pd.to_datetime(settled_debits['event_date'].min())
            max_d = pd.to_datetime(settled_debits['event_date'].max())
            days_hist = max(30, (max_d - min_d).days)
            daily_burn = (ess_debits['amount'].sum() / days_hist) * self.conservative_buffer
            for dt in daily_deltas:
                daily_deltas[dt] -= daily_burn

        return daily_deltas

    def simulate(
        self,
        ctx: RequestContext,
        recon: Dict[str, Any],
        plan_payments: Optional[List[Tuple[str, float]]] = None,
        spending_stops: Optional[Set[str]] = None,
        spending_reduces: Optional[Dict[str, float]] = None
    ) -> SimulationResult:
        """Simulates 90-day balance with given payment plan and spending adjustments."""
        daily_deltas = self.build_daily_deltas(ctx, recon, spending_stops, spending_reduces)

        # Map plan payments to dates
        payment_deltas: Dict[datetime.date, float] = {}
        if plan_payments:
            for d_str, p_amt in plan_payments:
                p_date = datetime.date.fromisoformat(d_str)
                payment_deltas[p_date] = payment_deltas.get(p_date, 0.0) + p_amt

        curr_bal = ctx.profile.current_available_balance
        min_bal = ctx.profile.minimum_balance_to_keep

        min_observed = curr_bal
        min_headroom = curr_bal - min_bal
        breach_date = None
        is_safe = True
        daily_balances: Dict[str, float] = {}

        for dt in sorted(daily_deltas.keys()):
            curr_bal += daily_deltas[dt]
            if dt in payment_deltas:
                curr_bal -= payment_deltas[dt]

            d_str = dt.strftime('%Y-%m-%d')
            daily_balances[d_str] = curr_bal

            headroom = curr_bal - min_bal
            if curr_bal < min_observed:
                min_observed = curr_bal
            if headroom < min_headroom:
                min_headroom = headroom

            if curr_bal < min_bal - 1e-4 and is_safe:
                is_safe = False
                breach_date = d_str

        return SimulationResult(
            is_safe=is_safe,
            min_balance_observed=min_observed,
            min_headroom=min_headroom,
            breach_date=breach_date,
            daily_balances=daily_balances
        )

    def calculate_amount_safe_to_pay(self, ctx: RequestContext, recon: Dict[str, Any]) -> float:
        """Calculates maximum amount safe to pay today (0 <= amt <= requested_amount)."""
        baseline = self.simulate(ctx, recon)
        max_safe = max(0.0, baseline.min_headroom)
        return min(ctx.requested_amount, max_safe)

    def calculate_earliest_date_for_full_payment(
        self,
        ctx: RequestContext,
        recon: Dict[str, Any]
    ) -> Optional[str]:
        """Finds the earliest date where paying requested_amount in full is safe without spending changes."""
        req_amt = ctx.requested_amount
        req_date = datetime.date.fromisoformat(ctx.request_date)
        end_date = req_date + datetime.timedelta(days=self.forecast_days)

        # Check if safe today
        sim_today = self.simulate(ctx, recon, plan_payments=[(ctx.request_date, req_amt)])
        if sim_today.is_safe:
            return ctx.request_date

        # Candidate dates: test every day from request_date + 1 to end_date
        total_days = (end_date - req_date).days
        for i in range(1, total_days + 1):
            cand_date = req_date + datetime.timedelta(days=i)
            cand_str = cand_date.strftime('%Y-%m-%d')
            sim_cand = self.simulate(ctx, recon, plan_payments=[(cand_str, req_amt)])
            if sim_cand.is_safe:
                return cand_str

        return None
