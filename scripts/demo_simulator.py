"""
Interactive & Batch Demonstration of the What-If Purchase & Payment Simulator

Demonstrates evaluating multiple purchase amounts and payment methods:
1. ₹60,000 — Full Payment
2. ₹60,000 — Partial Payment
3. ₹60,000 — Installments
4. ₹60,000 — Wait
5. ₹40,000 — Full Payment
6. ₹80,000 — Full Payment
"""

import sys
import os
import json
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_loader import load_all_data
from src.data_cleaner import clean_all_data
from src.data_joiner import DataJoiner
from src.image_extractor import ImageExtractor
from src.message_parser import MessageParser
from src.currency_converter import CurrencyConverter
from src.event_reconstructor import EventReconstructor
from src.forecast_engine import ForecastEngine
from src.payment_plans import PaymentPlanEngine
from src.decision_engine import DecisionEngine
from src.explanation_generator import ExplanationGenerator
from src.rag.rag_pipeline import RAGPipeline
from src.scenario_simulator import (
    ScenarioSimulator,
    ScenarioSpec,
    ScenarioResult,
    ScenarioComparison
)


def run_demo(request_id: str = 'request_01'):
    print("=" * 80)
    print(f"WHAT-IF PURCHASE & PAYMENT SIMULATOR DEMONSTRATION — {request_id}")
    print("=" * 80)

    # 1. Load data & initialize components
    print("\n1. Initializing System & Knowledge Base...")
    raw_data = load_all_data('dataset')
    clean_data = clean_all_data(raw_data)
    joiner = DataJoiner(clean_data)
    img_extractor = ImageExtractor()
    msg_parser = MessageParser()
    curr_converter = CurrencyConverter(clean_data['exchange_rates'])
    reconstructor = EventReconstructor(img_extractor, msg_parser, curr_converter)
    forecast_engine = ForecastEngine(forecast_days=90, conservative_buffer=1.0)
    plan_engine = PaymentPlanEngine()
    decision_engine = DecisionEngine(forecast_engine, plan_engine)

    # Initialize RAG Pipeline
    k_dir = 'knowledge'
    idx_file = os.path.join(k_dir, 'index.json')
    rag_pipe = None
    if os.path.exists(k_dir):
        rag_pipe = RAGPipeline(knowledge_dir=k_dir, index_path=idx_file, enabled=True)
        rag_pipe.build_index()

    explanation_gen = ExplanationGenerator(rag_pipeline=rag_pipe)

    simulator = ScenarioSimulator(
        data_joiner=joiner,
        event_reconstructor=reconstructor,
        forecast_engine=forecast_engine,
        decision_engine=decision_engine,
        plan_engine=plan_engine,
        explanation_generator=explanation_gen
    )

    base_ctx = joiner.get_request_context(request_id)
    curr = base_ctx.profile.home_currency
    print(f"User ID: {base_ctx.user_id} | Currency: {curr}")
    print(f"Current Available Balance: {base_ctx.profile.current_available_balance:,.2f} {curr}")
    print(f"Minimum Balance to Keep:   {base_ctx.profile.minimum_balance_to_keep:,.2f} {curr}")
    print(f"Allowed Payment Methods:   {base_ctx.profile.payment_methods_user_will_consider}")

    # 2. Define Scenarios
    print("\n2. Executing 6 What-If Scenarios...")
    specs = [
        ScenarioSpec(
            purchase_amount=60000.0,
            payment_method='full_payment',
            scenario_label='Scenario 1: 60k Full Payment'
        ),
        ScenarioSpec(
            purchase_amount=60000.0,
            payment_method='partial_payment',
            allows_partial_payment=True,
            scenario_label='Scenario 2: 60k Partial Payment'
        ),
        ScenarioSpec(
            purchase_amount=60000.0,
            payment_method='installments',
            scenario_label='Scenario 3: 60k Installments'
        ),
        ScenarioSpec(
            purchase_amount=60000.0,
            payment_method='wait',
            scenario_label='Scenario 4: 60k Wait'
        ),
        ScenarioSpec(
            purchase_amount=40000.0,
            payment_method='full_payment',
            scenario_label='Scenario 5: 40k Full Payment'
        ),
        ScenarioSpec(
            purchase_amount=80000.0,
            payment_method='full_payment',
            scenario_label='Scenario 6: 80k Full Payment'
        )
    ]

    comparison = simulator.simulate_scenarios(request_id, specs)

    # 3. Print Detailed Scenario Results
    print("\n" + "=" * 80)
    print("DETAILED SCENARIO RESULTS (Required Output Fields)")
    print("=" * 80)

    for idx, s in enumerate(comparison.scenarios, 1):
        print(f"\n--- [{s.scenario_label}] ---")
        print(f"  • purchase_amount:                {s.purchase_amount:,.2f} {curr}")
        print(f"  • payment_method:                 {s.payment_method}")
        print(f"  • affordability_status:           {s.affordability_status}")
        print(f"  • amount_safe_to_pay:             {s.amount_safe_to_pay:,.2f} {curr}")
        print(f"  • payment_plan:                   {s.payment_plan}")
        print(f"  • earliest_date_for_full_payment: {s.earliest_date_for_full_payment}")
        print(f"  • spending_changes_needed:        {s.spending_changes_needed}")
        print(f"  • minimum_projected_balance:      {s.minimum_projected_balance:,.2f} {curr}")
        print(f"  • decision_explanation:           {s.decision_explanation[:140]}...")

    # 4. Print Comparison Table
    print("\n" + "=" * 80)
    print("SCENARIO COMPARISON TABLE")
    print("=" * 80)
    print(comparison.to_markdown())

    # 5. Best Scenario Selected by Safe Plan Ranking Rules
    print("\n" + "=" * 80)
    print("BEST RECOMMENDED SCENARIO (PRD Section 4.4 Ranking)")
    print("=" * 80)
    best = comparison.best_scenario
    if best:
        print(f"Label:                 {best.scenario_label}")
        print(f"Purchase Amount:       {best.purchase_amount:,.2f} {curr}")
        print(f"Method:                {best.payment_method}")
        print(f"Affordability Status:  {best.affordability_status}")
        print(f"Plan:                  {best.payment_plan}")
        print(f"Min Projected Balance: {best.minimum_projected_balance:,.2f} {curr}")
        print(f"Summary:               {comparison.comparison_summary}")
    print("=" * 80)


if __name__ == '__main__':
    req_id = sys.argv[1] if len(sys.argv) > 1 else 'request_01'
    run_demo(req_id)
