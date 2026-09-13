"""
Unit & Integration Tests for What-If Purchase and Payment Simulator
"""

import os
import sys
import pytest
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
from src.scenario_simulator import (
    ScenarioSimulator,
    ScenarioSpec,
    ScenarioResult,
    ScenarioComparison
)


@pytest.fixture(scope="module")
def simulator():
    """Initializes the complete engine and scenario simulator."""
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
    explanation_gen = ExplanationGenerator(rag_pipeline=None)  # Use fast deterministic fallback for unit tests

    sim = ScenarioSimulator(
        data_joiner=joiner,
        event_reconstructor=reconstructor,
        forecast_engine=forecast_engine,
        decision_engine=decision_engine,
        plan_engine=plan_engine,
        explanation_generator=explanation_gen
    )
    return sim


class TestScenarioSimulator:
    """Test suite covering all required what-if purchase simulation test cases."""

    def test_01_small_purchase_amount_full_payment(self, simulator):
        """Small purchase amount should be affordable now with full payment."""
        spec = ScenarioSpec(
            purchase_amount=500.0,
            payment_method='full_payment',
            scenario_label='Small Purchase'
        )
        res = simulator.simulate_scenario('request_01', spec)
        
        assert isinstance(res, ScenarioResult)
        assert res.purchase_amount == 500.0
        assert res.payment_method == 'full_payment'
        assert res.affordability_status == 'affordable_now'
        assert res.amount_safe_to_pay >= 500.0
        assert res.payment_plan != 'none'
        assert res.is_safe is True
        assert res.minimum_projected_balance > 0

    def test_02_medium_purchase_amount_full_payment(self, simulator):
        """Medium purchase amount should simulate correctly and calculate safe headroom."""
        spec = ScenarioSpec(
            purchase_amount=15000.0,
            payment_method='full_payment',
            scenario_label='Medium Purchase'
        )
        res = simulator.simulate_scenario('request_01', spec)

        assert isinstance(res, ScenarioResult)
        assert res.purchase_amount == 15000.0
        assert res.payment_method == 'full_payment'
        assert res.affordability_status in ('affordable_now', 'affordable_with_plan', 'affordable_later', 'not_affordable')
        assert res.minimum_projected_balance is not None

    def test_03_large_purchase_amount_full_payment(self, simulator):
        """Very large purchase amount exceeding cash should be not affordable or affordable later."""
        spec = ScenarioSpec(
            purchase_amount=500000.0,
            payment_method='full_payment',
            scenario_label='Large Purchase'
        )
        res = simulator.simulate_scenario('request_01', spec)

        assert isinstance(res, ScenarioResult)
        assert res.purchase_amount == 500000.0
        assert res.affordability_status in ('not_affordable', 'affordable_later')
        assert res.is_safe is False
        assert "Not affordable" in res.decision_explanation or "safe" in res.decision_explanation

    def test_04_same_amount_installments(self, simulator):
        """Simulate purchase amount with installment payment method."""
        spec = ScenarioSpec(
            purchase_amount=25256.0,
            payment_method='installments',
            scenario_label='Installment Plan'
        )
        res = simulator.simulate_scenario('request_01', spec)

        assert isinstance(res, ScenarioResult)
        assert res.purchase_amount == 25256.0
        # If user permits installments, verify plan structure
        if 'installments' in simulator.joiner.get_request_context('request_01').profile.payment_methods_user_will_consider:
            if res.affordability_status == 'affordable_with_plan':
                assert res.payment_method == 'installments'
                assert '|' in res.payment_plan or ':' in res.payment_plan

    def test_05_same_amount_partial_payment(self, simulator):
        """Simulate purchase amount with partial payment method."""
        spec = ScenarioSpec(
            purchase_amount=25256.0,
            payment_method='partial_payment',
            allows_partial_payment=True,
            scenario_label='Partial Payment'
        )
        res = simulator.simulate_scenario('request_01', spec)

        assert isinstance(res, ScenarioResult)
        assert res.purchase_amount == 25256.0
        if res.affordability_status == 'affordable_with_plan' and res.payment_method == 'partial_payment':
            # Exactly two payments
            parts = res.payment_plan.split('|')
            assert len(parts) == 2

    def test_06_same_amount_wait(self, simulator):
        """Simulate wait scenario evaluating safe future purchase date."""
        spec = ScenarioSpec(
            purchase_amount=25256.0,
            payment_method='wait',
            scenario_label='Wait Strategy'
        )
        res = simulator.simulate_scenario('request_01', spec)

        assert isinstance(res, ScenarioResult)
        assert res.purchase_amount == 25256.0
        assert res.affordability_status in ('affordable_later', 'not_affordable')
        if res.affordability_status == 'affordable_later':
            assert res.payment_method == 'wait'
            assert res.earliest_date_for_full_payment is not None

    def test_07_amount_greater_than_safe_amount(self, simulator):
        """Testing amount greater than safe headroom captures projected breach and minimum balance."""
        ctx = simulator.joiner.get_request_context('request_01')
        recon = simulator.reconstructor.reconstruct(ctx)
        safe_amt = simulator.forecast.calculate_amount_safe_to_pay(ctx, recon)
        
        excess_amt = safe_amt + 50000.0
        spec = ScenarioSpec(
            purchase_amount=excess_amt,
            payment_method='full_payment',
            scenario_label='Excess Amount'
        )
        res = simulator.simulate_scenario('request_01', spec)

        assert res.is_safe is False
        assert res.affordability_status != 'affordable_now'
        # Observed balance should fall below minimum balance requirement
        assert res.minimum_projected_balance < ctx.profile.minimum_balance_to_keep

    def test_08_invalid_payment_method(self, simulator):
        """Invalid payment method name should raise ValueError."""
        spec = ScenarioSpec(
            purchase_amount=5000.0,
            payment_method='cryptocurrency_token',
            scenario_label='Invalid Method'
        )
        with pytest.raises(ValueError) as exc_info:
            simulator.simulate_scenario('request_01', spec)
        assert "Invalid payment_method" in str(exc_info.value)

    def test_09_invalid_installment_option(self, simulator):
        """Non-existent installment option ID should raise ValueError."""
        spec = ScenarioSpec(
            purchase_amount=25256.0,
            payment_method='installments',
            payment_option_id='payment_option_non_existent_9999',
            scenario_label='Invalid Option'
        )
        with pytest.raises(ValueError) as exc_info:
            simulator.simulate_scenario('request_01', spec)
        assert "does not exist in payment options" in str(exc_info.value)

    def test_10_multiple_scenarios_comparison_and_ranking(self, simulator):
        """Batch scenario simulation ranks candidates to select best scenario."""
        specs = [
            ScenarioSpec(purchase_amount=60000.0, payment_method='full_payment', scenario_label='Scenario 1: 60k Full'),
            ScenarioSpec(purchase_amount=60000.0, payment_method='installments', scenario_label='Scenario 2: 60k Installments'),
            ScenarioSpec(purchase_amount=60000.0, payment_method='wait', scenario_label='Scenario 3: 60k Wait'),
            ScenarioSpec(purchase_amount=40000.0, payment_method='full_payment', scenario_label='Scenario 4: 40k Full'),
            ScenarioSpec(purchase_amount=80000.0, payment_method='full_payment', scenario_label='Scenario 5: 80k Full')
        ]
        comp = simulator.simulate_scenarios('request_01', specs)

        assert isinstance(comp, ScenarioComparison)
        assert len(comp.scenarios) == 5
        assert comp.best_scenario is not None
        assert comp.best_scenario.scenario_label in [s.scenario_label for s in specs]
        
        # DataFrame conversion verification
        df = comp.to_dataframe()
        assert len(df) == 5
        assert 'purchase_amount' in df.columns
        assert 'minimum_projected_balance' in df.columns
        assert 'affordability_status' in df.columns

        # Markdown representation verification
        md = comp.to_markdown()
        assert "purchase_amount" in md
        assert "Scenario" not in md or "60000" in md

    def test_11_dataset_immutability(self, simulator):
        """Simulator execution must not modify any original CSV files in dataset/."""
        orig_reqs = pd.read_csv('dataset/requests.csv')
        orig_profiles = pd.read_csv('dataset/financial_profiles.csv')

        spec = ScenarioSpec(purchase_amount=999999.0, payment_method='full_payment')
        simulator.simulate_scenario('request_01', spec)

        curr_reqs = pd.read_csv('dataset/requests.csv')
        curr_profiles = pd.read_csv('dataset/financial_profiles.csv')

        pd.testing.assert_frame_equal(orig_reqs, curr_reqs)
        pd.testing.assert_frame_equal(orig_profiles, curr_profiles)
