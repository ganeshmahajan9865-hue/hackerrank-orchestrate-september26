"""
What-If Purchase and Payment Simulator Module

Allows users and financial advisors to test hypothetical purchase amounts
and payment methods without modifying original dataset files or altering
existing decision logic.

Reuses:
- ForecastEngine (90-day cash flow simulation and headroom checks)
- DecisionEngine (candidate plan generation and PRD Section 4.4 ranking)
- PaymentPlanEngine (plan formatting and schedule verification)
- CurrencyConverter (fixed dated FX handling)
- ExplanationGenerator / RAGPipeline (grounded financial explanations)
- OutputValidator (mathematical and schema integrity checks)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import copy
import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple, Optional, Any, Union
import pandas as pd

from src.data_joiner import RequestContext, UserProfile, DataJoiner
from src.event_reconstructor import EventReconstructor
from src.forecast_engine import ForecastEngine, SimulationResult
from src.payment_plans import PaymentPlanEngine, CandidatePlan, format_amount
from src.decision_engine import DecisionEngine, DecisionResult
from src.explanation_generator import ExplanationGenerator
from src.validator import OutputValidator


VALID_PAYMENT_METHODS = {
    'full_payment',
    'partial_payment',
    'installments',
    'wait',
    'any'  # Evaluates all permitted methods and picks optimal
}


@dataclass
class ScenarioSpec:
    """Specification of a hypothetical purchase scenario to simulate."""
    purchase_amount: float
    payment_method: Optional[str] = None  # 'full_payment', 'partial_payment', 'installments', 'wait', or None/'any'
    payment_option_id: Optional[str] = None  # Specific installment option from dataset
    desired_completion_date: Optional[str] = None  # Custom completion deadline YYYY-MM-DD
    allows_partial_payment: Optional[bool] = None  # Override partial payment permission
    scenario_label: Optional[str] = None  # User-friendly label (e.g. 'Scenario A')


@dataclass
class ScenarioResult:
    """Result of simulating a single what-if purchase scenario."""
    purchase_amount: float
    payment_method: str
    affordability_status: str
    amount_safe_to_pay: float
    payment_plan: str
    earliest_date_for_full_payment: Optional[str]
    spending_changes_needed: str
    minimum_projected_balance: float
    decision_explanation: str
    
    # Supplemental metadata
    scenario_label: Optional[str] = None
    is_safe: bool = False
    breach_date: Optional[str] = None
    meets_desired_deadline: bool = True
    total_cost: float = 0.0
    payment_option_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Returns standard dictionary of required output fields."""
        return {
            'purchase_amount': self.purchase_amount,
            'payment_method': self.payment_method,
            'affordability_status': self.affordability_status,
            'amount_safe_to_pay': self.amount_safe_to_pay,
            'payment_plan': self.payment_plan,
            'earliest_date_for_full_payment': self.earliest_date_for_full_payment,
            'spending_changes_needed': self.spending_changes_needed,
            'minimum_projected_balance': self.minimum_projected_balance,
            'decision_explanation': self.decision_explanation
        }


@dataclass
class ScenarioComparison:
    """Collection and comparison of multiple simulated scenarios."""
    scenarios: List[ScenarioResult]
    best_scenario: Optional[ScenarioResult] = None
    comparison_summary: str = ""

    def to_dataframe(self) -> pd.DataFrame:
        """Converts results into a pandas DataFrame."""
        rows = [s.to_dict() for s in self.scenarios]
        return pd.DataFrame(rows)

    def to_markdown(self) -> str:
        """Formats scenario comparison as a Markdown table without external dependencies."""
        df = self.to_dataframe()
        cols = [
            'purchase_amount', 'payment_method', 'affordability_status',
            'amount_safe_to_pay', 'payment_plan', 'earliest_date_for_full_payment',
            'minimum_projected_balance'
        ]
        sub_df = df[[c for c in cols if c in df.columns]]
        header = "| " + " | ".join(sub_df.columns) + " |"
        sep = "| " + " | ".join(["---"] * len(sub_df.columns)) + " |"
        rows = [header, sep]
        for _, row in sub_df.iterrows():
            row_str = "| " + " | ".join(str(val) if pd.notna(val) else "" for val in row) + " |"
            rows.append(row_str)
        return "\n".join(rows)


class ScenarioSimulator:
    """
    What-If Purchase and Payment Simulator.
    
    Simulates alternative purchase amounts and payment structures using
    the existing 90-day cash flow simulation and constraint-ranking engines.
    Does not modify any original datasets or underlying profiles.
    """

    def __init__(
        self,
        data_joiner: DataJoiner,
        event_reconstructor: EventReconstructor,
        forecast_engine: ForecastEngine,
        decision_engine: DecisionEngine,
        plan_engine: PaymentPlanEngine,
        explanation_generator: ExplanationGenerator
    ):
        self.joiner = data_joiner
        self.reconstructor = event_reconstructor
        self.forecast = forecast_engine
        self.decision = decision_engine
        self.plan_engine = plan_engine
        self.explanation_gen = explanation_generator
        self.validator = OutputValidator(data_joiner)

    def _create_ephemeral_context(
        self,
        base_ctx: RequestContext,
        spec: ScenarioSpec
    ) -> RequestContext:
        """
        Creates an isolated, in-memory clone of RequestContext tailored
        to the specified scenario without touching any original data files.
        """
        # Deepcopy profile to protect original state
        profile_copy = copy.deepcopy(base_ctx.profile)

        # Handle payment method restriction if specified
        target_method = spec.payment_method
        if target_method and target_method != 'any':
            if target_method not in VALID_PAYMENT_METHODS:
                raise ValueError(
                    f"Invalid payment_method '{target_method}'. "
                    f"Must be one of {sorted(list(VALID_PAYMENT_METHODS))}."
                )

        # Payment options slice
        payment_options_copy = base_ctx.payment_options.copy(deep=True)

        if spec.payment_option_id:
            matching_opts = payment_options_copy[
                payment_options_copy['payment_option_id'] == spec.payment_option_id
            ]
            if matching_opts.empty:
                raise ValueError(
                    f"Invalid installment option '{spec.payment_option_id}': "
                    f"does not exist in payment options for request '{base_ctx.request_id}'."
                )
            payment_options_copy = matching_opts.copy()

        # Adjust installment payment amounts proportionally if purchase_amount changed
        if abs(spec.purchase_amount - base_ctx.requested_amount) > 1e-4 and not payment_options_copy.empty:
            orig_amt = base_ctx.requested_amount
            scale = spec.purchase_amount / orig_amt if orig_amt > 0 else 1.0
            
            # Update payment options for the simulated purchase amount
            for idx in payment_options_copy.index:
                if payment_options_copy.loc[idx, 'payment_method'] == 'installments':
                    payment_options_copy.loc[idx, 'payment_amount'] = round(
                        float(payment_options_copy.loc[idx, 'payment_amount']) * scale, 2
                    )
                    payment_options_copy.loc[idx, 'total_payable_amount'] = round(
                        float(payment_options_copy.loc[idx, 'total_payable_amount']) * scale, 2
                    )
                    payment_options_copy.loc[idx, 'financing_fee'] = round(
                        float(payment_options_copy.loc[idx, 'financing_fee']) * scale, 2
                    )

        # Set partial payment permission
        partial_allowed = (
            spec.allows_partial_payment
            if spec.allows_partial_payment is not None
            else base_ctx.allows_partial_payment
        )

        # Completion deadline
        deadline = spec.desired_completion_date or base_ctx.desired_completion_date

        return RequestContext(
            request_id=f"{base_ctx.request_id}_sim",
            user_id=base_ctx.user_id,
            request_date=base_ctx.request_date,
            request_type=base_ctx.request_type,
            requested_amount=float(spec.purchase_amount),
            desired_completion_date=deadline,
            allows_partial_payment=partial_allowed,
            request_text=f"Simulated purchase of {spec.purchase_amount} {base_ctx.profile.home_currency}",
            profile=profile_copy,
            events=base_ctx.events.copy(deep=True),
            payment_options=payment_options_copy,
            messages=base_ctx.messages.copy(deep=True),
            images=base_ctx.images.copy(deep=True)
        )

    def simulate_scenario(
        self,
        base_request: Union[str, RequestContext],
        spec: ScenarioSpec
    ) -> ScenarioResult:
        """
        Executes a single what-if scenario.
        
        Args:
            base_request: Existing request_id (e.g. 'request_01') or a RequestContext object.
            spec: ScenarioSpec specifying purchase amount, payment method, etc.
            
        Returns:
            ScenarioResult containing all required output fields.
        """
        if isinstance(base_request, str):
            base_ctx = self.joiner.get_request_context(base_request)
        else:
            base_ctx = base_request

        if spec.purchase_amount <= 0:
            raise ValueError(f"Purchase amount must be positive, got {spec.purchase_amount}.")

        # 1. Build ephemeral scenario context
        ctx = self._create_ephemeral_context(base_ctx, spec)
        recon = self.reconstructor.reconstruct(ctx)

        target_method = spec.payment_method or 'any'

        # 2. Check method eligibility against user profile preferences
        allowed_by_user = set(ctx.profile.payment_methods_user_will_consider or [])
        if target_method != 'any' and target_method != 'wait' and target_method not in allowed_by_user:
            # User specifically rejects this payment method in their profile
            amount_safe = self.forecast.calculate_amount_safe_to_pay(ctx, recon)
            earliest_full = self.forecast.calculate_earliest_date_for_full_payment(ctx, recon)
            min_bal = ctx.profile.current_available_balance
            explanation = (
                f"User payment preferences strictly disallow '{target_method}'. "
                f"Considered payment methods for this profile are: {sorted(list(allowed_by_user))}."
            )
            return ScenarioResult(
                purchase_amount=spec.purchase_amount,
                payment_method=target_method,
                affordability_status='not_affordable',
                amount_safe_to_pay=amount_safe,
                payment_plan='none',
                earliest_date_for_full_payment=earliest_full,
                spending_changes_needed='none',
                minimum_projected_balance=round(min_bal, 2),
                decision_explanation=explanation,
                scenario_label=spec.scenario_label,
                is_safe=False,
                breach_date=None,
                meets_desired_deadline=False,
                total_cost=0.0
            )

        # 3. Restrict considered methods to target_method if specific method is requested
        if target_method != 'any':
            if target_method == 'wait':
                # Wait evaluates future full payment without spending changes
                ctx.profile.payment_methods_user_will_consider = ['full_payment']
            else:
                ctx.profile.payment_methods_user_will_consider = [target_method]

        # 4. Evaluate using existing DecisionEngine
        decision = self.decision.evaluate(ctx, recon)

        # 5. Handle specific method constraints
        if target_method == 'wait':
            req_date = ctx.request_date
            earliest_full = decision.earliest_date_for_full_payment
            if earliest_full and earliest_full > req_date:
                wait_plan = self.plan_engine.build_wait_plan(ctx, earliest_full)
                sim_wait = self.forecast.simulate(ctx, recon, wait_plan.payments)
                decision = DecisionResult(
                    request_id=ctx.request_id,
                    amount_safe_to_pay=decision.amount_safe_to_pay,
                    affordability_status='affordable_later',
                    recommended_payment_method='wait',
                    payment_plan=wait_plan.formatted_plan,
                    earliest_date_for_full_payment=earliest_full,
                    spending_changes_needed='none',
                    chosen_plan=wait_plan
                )
            else:
                fallback = self.plan_engine.build_not_recommended_plan()
                decision = DecisionResult(
                    request_id=ctx.request_id,
                    amount_safe_to_pay=decision.amount_safe_to_pay,
                    affordability_status='not_affordable',
                    recommended_payment_method='not_recommended',
                    payment_plan='none',
                    earliest_date_for_full_payment=earliest_full,
                    spending_changes_needed='none',
                    chosen_plan=fallback
                )
        elif target_method != 'any':
            # If a specific method was requested, verify if the engine was able to recommend it
            if decision.recommended_payment_method != target_method:
                # The requested method was not safe or feasible
                decision.affordability_status = 'not_affordable'
                decision.recommended_payment_method = 'not_recommended'
                decision.payment_plan = 'none'

        # 6. Simulate plan to determine minimum_projected_balance
        stops = set()
        reduces = {}
        if decision.chosen_plan and decision.chosen_plan.spending_changes:
            for sc in decision.chosen_plan.spending_changes:
                parts = sc.split(':')
                if parts[0] == 'stop':
                    stops.add(parts[1])
                elif parts[0] == 'reduce_to':
                    reduces[parts[1]] = float(parts[2])

        if decision.chosen_plan and decision.chosen_plan.payments:
            sim = self.forecast.simulate(ctx, recon, decision.chosen_plan.payments, stops, reduces)
            min_bal_observed = sim.min_balance_observed
            is_safe = sim.is_safe
            breach_date = sim.breach_date
        else:
            # If no safe plan, simulate paying the requested amount directly on request_date
            # to observe the resulting breach and true cash minimum
            test_payments = [(ctx.request_date, spec.purchase_amount)]
            sim_breach = self.forecast.simulate(ctx, recon, test_payments)
            min_bal_observed = sim_breach.min_balance_observed
            is_safe = False
            breach_date = sim_breach.breach_date

        # 7. Generate explanation using existing ExplanationGenerator (with RAG)
        explanation = self.explanation_gen.generate(ctx, decision)

        # If a specific method was forced and proved unaffordable, tailor explanation clarity
        if target_method != 'any' and decision.affordability_status == 'not_affordable':
            if breach_date:
                explanation = (
                    f"Testing {target_method} for {format_amount(spec.purchase_amount)} {ctx.profile.home_currency}: "
                    f"Not affordable. Cash balance would breach required minimum ({format_amount(ctx.profile.minimum_balance_to_keep)}) "
                    f"dropping to {format_amount(min_bal_observed)} on {breach_date}. "
                    + explanation
                )

        chosen_plan = decision.chosen_plan
        meets_deadline = chosen_plan.is_within_deadline(ctx.desired_completion_date) if chosen_plan else False
        tot_cost = chosen_plan.total_cost if chosen_plan else spec.purchase_amount
        opt_id = chosen_plan.payment_option_id if chosen_plan else spec.payment_option_id

        return ScenarioResult(
            purchase_amount=spec.purchase_amount,
            payment_method=target_method if target_method != 'any' else decision.recommended_payment_method,
            affordability_status=decision.affordability_status,
            amount_safe_to_pay=decision.amount_safe_to_pay,
            payment_plan=decision.payment_plan,
            earliest_date_for_full_payment=decision.earliest_date_for_full_payment,
            spending_changes_needed=decision.spending_changes_needed,
            minimum_projected_balance=round(min_bal_observed, 2),
            decision_explanation=explanation,
            scenario_label=spec.scenario_label,
            is_safe=is_safe,
            breach_date=breach_date,
            meets_desired_deadline=meets_deadline,
            total_cost=tot_cost,
            payment_option_id=opt_id
        )

    def simulate_scenarios(
        self,
        base_request: Union[str, RequestContext],
        specs: List[ScenarioSpec]
    ) -> ScenarioComparison:
        """
        Simulates a batch of scenarios and ranks valid options using PRD Section 4.4 rules.
        """
        results: List[ScenarioResult] = []
        for s in specs:
            res = self.simulate_scenario(base_request, s)
            results.append(res)

        # Rank valid scenarios using the exact safe-plan ranking hierarchy
        def scenario_rank_key(res: ScenarioResult):
            # 1. Affordability status priority (affordable_now > affordable_with_plan > affordable_later > not_affordable)
            status_priority = {
                'affordable_now': 0,
                'affordable_with_plan': 1,
                'affordable_later': 2,
                'not_affordable': 3
            }.get(res.affordability_status, 4)

            # 2. Meets completion deadline
            meets_deadline = 0 if res.meets_desired_deadline else 1

            # 3. Requires fewer spending changes
            has_changes = 0 if res.spending_changes_needed == 'none' else len(res.spending_changes_needed.split('|'))

            # 4. Minimizes total amount paid
            cost = res.total_cost

            # 5. Starts payment earlier
            start_date = '9999-12-31'
            if res.payment_plan != 'none':
                first_entry = res.payment_plan.split('|')[0]
                if ':' in first_entry:
                    start_date = first_entry.split(':')[0]

            # 6. Fewer payments
            num_pmts = 1
            if res.payment_plan != 'none':
                num_pmts = len(res.payment_plan.split('|'))

            # 7. Lowest option ID
            opt = res.payment_option_id or ''

            return (status_priority, meets_deadline, has_changes, cost, start_date, num_pmts, opt)

        # Identify best valid scenario
        sorted_results = sorted(results, key=scenario_rank_key)
        best = sorted_results[0] if sorted_results else None

        # Generate comparative summary
        summary_lines = [
            f"Evaluated {len(results)} hypothetical purchase scenario(s).",
            f"Best recommended scenario: '{best.scenario_label or best.payment_method}' "
            f"({best.affordability_status}, method={best.payment_method}, safe_amount={best.amount_safe_to_pay})."
        ] if best else ["No scenarios evaluated."]

        return ScenarioComparison(
            scenarios=results,
            best_scenario=best,
            comparison_summary="\n".join(summary_lines)
        )

    def simulate_amount_variations(
        self,
        base_request: Union[str, RequestContext],
        amounts: List[float],
        methods: Optional[List[str]] = None
    ) -> ScenarioComparison:
        """
        Convenience method to test multiple purchase amounts across different payment methods.
        """
        methods = methods or ['full_payment', 'installments', 'wait']
        specs = []
        for amt in amounts:
            for m in methods:
                specs.append(ScenarioSpec(
                    purchase_amount=amt,
                    payment_method=m,
                    scenario_label=f"Amount {amt} - {m}"
                ))
        return self.simulate_scenarios(base_request, specs)
