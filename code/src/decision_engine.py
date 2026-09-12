"""
Decision Engine Module

Determines:
- amount_safe_to_pay
- affordability_status
- recommended_payment_method
- payment_plan
- earliest_date_for_full_payment
- spending_changes_needed

Strict deterministic ranking hierarchy according to PRD Section 4.4.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set, Any
import itertools
import datetime
import pandas as pd

from src.data_joiner import RequestContext
from src.forecast_engine import ForecastEngine, SimulationResult
from src.payment_plans import PaymentPlanEngine, CandidatePlan, format_amount


@dataclass
class DecisionResult:
    request_id: str
    amount_safe_to_pay: float
    affordability_status: str
    recommended_payment_method: str
    payment_plan: str
    earliest_date_for_full_payment: Optional[str]
    spending_changes_needed: str
    chosen_plan: CandidatePlan


class DecisionEngine:
    """Evaluates candidate plans, explores flexible spending adjustments, and ranks safe solutions."""

    def __init__(self, forecast_engine: ForecastEngine, plan_engine: PaymentPlanEngine):
        self.forecast = forecast_engine
        self.plan_engine = plan_engine

    def _get_flexible_spending_options(self, ctx: RequestContext, recon: Dict[str, Any]) -> List[Tuple[str, str, Optional[float]]]:
        """
        Identifies eligible spending change actions:
        Returns list of (action_type, event_id, new_amount).
        Only non-protected, flexible recurring commitments user is willing to stop/reduce.
        """
        options = []
        willing_stop = set(ctx.profile.expense_categories_user_is_willing_to_stop or [])
        willing_reduce = set(ctx.profile.expense_categories_user_is_willing_to_reduce or [])
        protected = set(ctx.profile.expense_categories_to_protect or [])

        # 1. From recurring commitments
        for c in recon['recurring_commitments']:
            cat = c.category
            ev_id = c.sample_event_id
            flex = c.flexibility

            if cat in protected:
                continue

            # Stoppable
            if (cat in willing_stop) and flex in ('stoppable', 'reducible_or_stoppable'):
                options.append(('stop', ev_id, None))

            # Reducible
            if (cat in willing_reduce) and flex in ('reducible', 'reducible_or_stoppable'):
                if c.minimum_allowed_amount is not None:
                    options.append(('reduce_to', ev_id, c.minimum_allowed_amount))

        # 2. Also check past debit events in ctx.events for flexible categories (e.g. dining event_989)
        evs = ctx.events
        flex_evs = evs[(evs['direction'] == 'debit') & (evs['event_date'] <= ctx.request_date) & (evs['status'] == 'settled')]
        seen_events = {ev_id for _, ev_id, _ in options}
        for cat in (willing_stop | willing_reduce):
            if cat in protected:
                continue
            cat_evs = flex_evs[flex_evs['category'] == cat]
            if len(cat_evs) > 0:
                latest = cat_evs.sort_values('event_date').iloc[-1]
                ev_id = str(latest['event_id'])
                if ev_id in seen_events:
                    continue
                flex = str(latest['flexibility'])
                min_amt = None
                if pd.notna(latest['minimum_allowed_amount']):
                    min_amt = float(latest['minimum_allowed_amount'])

                if (cat in willing_stop) and flex in ('stoppable', 'reducible_or_stoppable'):
                    options.append(('stop', ev_id, None))
                    seen_events.add(ev_id)
                if (cat in willing_reduce) and flex in ('reducible', 'reducible_or_stoppable'):
                    if min_amt is not None:
                        options.append(('reduce_to', ev_id, min_amt))
                        seen_events.add(ev_id)

        return options

    def evaluate(self, ctx: RequestContext, recon: Dict[str, Any]) -> DecisionResult:
        """Determines optimal recommendation for the request context."""
        req_id = ctx.request_id
        req_amt = ctx.requested_amount
        req_date = ctx.request_date
        desired_deadline = ctx.desired_completion_date

        # 1. Base calculations without spending changes
        amount_safe = self.forecast.calculate_amount_safe_to_pay(ctx, recon)
        earliest_full = self.forecast.calculate_earliest_date_for_full_payment(ctx, recon)

        # 2. Collect candidate spending change sets (from 0 changes up to 3 changes)
        flex_options = self._get_flexible_spending_options(ctx, recon)
        change_sets: List[List[Tuple[str, str, Optional[float]]]] = [[]]

        for k in [1, 2, 3]:
            for combo in itertools.combinations(flex_options, k):
                # Ensure no event is both stopped and reduced
                event_ids = [x[1] for x in combo]
                if len(event_ids) == len(set(event_ids)):
                    change_sets.append(list(combo))

        # 3. Evaluate candidate plans
        safe_plans: List[Tuple[CandidatePlan, SimulationResult]] = []

        allowed_methods = ctx.profile.payment_methods_user_will_consider

        for changes in change_sets:
            # Format changes
            stops = {ev_id for act, ev_id, _ in changes if act == 'stop'}
            reduces = {ev_id: amt for act, ev_id, amt in changes if act == 'reduce_to'}
            change_strings = []
            for act, ev_id, amt in changes:
                if act == 'stop':
                    change_strings.append(f"stop:{ev_id}")
                else:
                    change_strings.append(f"reduce_to:{ev_id}:{format_amount(amt)}")

            # Candidate A: Full Payment
            if 'full_payment' in allowed_methods:
                full_plan = self.plan_engine.build_full_payment_plan(ctx, change_strings)
                sim = self.forecast.simulate(ctx, recon, full_plan.payments, stops, reduces)
                if sim.is_safe:
                    safe_plans.append((full_plan, sim))

            # Candidate B: Installments
            if 'installments' in allowed_methods:
                inst_plans = self.plan_engine.build_installment_plans(ctx, change_strings)
                for ip in inst_plans:
                    sim = self.forecast.simulate(ctx, recon, ip.payments, stops, reduces)
                    if sim.is_safe:
                        safe_plans.append((ip, sim))

            # Candidate C: Partial Payment (only tested without spending changes per PRD)
            if len(changes) == 0 and 'partial_payment' in allowed_methods:
                partial_plan = self.plan_engine.build_partial_payment_plan(ctx, amount_safe, earliest_full, change_strings)
                if partial_plan:
                    sim = self.forecast.simulate(ctx, recon, partial_plan.payments, stops, reduces)
                    if sim.is_safe:
                        safe_plans.append((partial_plan, sim))

        # Candidate D: Wait (evaluated if full_payment becomes safe in future without spending changes)
        if 'full_payment' in allowed_methods and earliest_full and earliest_full > req_date:
            wait_plan = self.plan_engine.build_wait_plan(ctx, earliest_full)
            if wait_plan:
                sim = self.forecast.simulate(ctx, recon, wait_plan.payments)
                if sim.is_safe:
                    safe_plans.append((wait_plan, sim))

        # 4. Rank safe plans according to PRD Section 4.4
        def plan_rank_key(item: Tuple[CandidatePlan, SimulationResult]):
            p, _ = item
            # 1. Meets desired_completion_date
            meets_deadline = 0 if p.is_within_deadline(desired_deadline) else 1
            # 2. Requires no spending changes
            has_changes = len(p.spending_changes)
            # 3. Minimizes total amount paid
            tot_cost = p.total_cost
            # 4. Starts payment earlier
            start_d = p.start_date
            # 5. Fewer payments
            num_payments = p.number_of_payments
            # 6. Lowest payment_option_id
            opt_id = p.payment_option_id or ''
            return (meets_deadline, has_changes, tot_cost, start_d, num_payments, opt_id)

        if not safe_plans:
            fallback = self.plan_engine.build_not_recommended_plan()
            return DecisionResult(
                request_id=req_id,
                amount_safe_to_pay=amount_safe,
                affordability_status='not_affordable',
                recommended_payment_method='not_recommended',
                payment_plan='none',
                earliest_date_for_full_payment=earliest_full,
                spending_changes_needed='none',
                chosen_plan=fallback
            )

        safe_plans.sort(key=plan_rank_key)
        best_plan, _ = safe_plans[0]

        # Determine affordability status
        if best_plan.plan_type == 'full_payment':
            if len(best_plan.spending_changes) == 0:
                afford_status = 'affordable_now'
                earliest_full = req_date
            else:
                afford_status = 'affordable_with_plan'
        elif best_plan.plan_type in ('installments', 'partial_payment'):
            afford_status = 'affordable_with_plan'
        elif best_plan.plan_type == 'wait':
            afford_status = 'affordable_later'
        else:
            afford_status = 'not_affordable'

        spending_str = '|'.join(best_plan.spending_changes) if best_plan.spending_changes else 'none'

        return DecisionResult(
            request_id=req_id,
            amount_safe_to_pay=amount_safe,
            affordability_status=afford_status,
            recommended_payment_method=best_plan.plan_type,
            payment_plan=best_plan.formatted_plan,
            earliest_date_for_full_payment=earliest_full,
            spending_changes_needed=spending_str,
            chosen_plan=best_plan
        )
