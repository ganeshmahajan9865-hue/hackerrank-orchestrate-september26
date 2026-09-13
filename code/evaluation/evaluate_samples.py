"""
Evaluation Workflow Module — Buy or Wait?

Independent evaluation harness that:
1. Loads validation requests from dataset/sample_requests.csv
2. Executes the financial prediction pipeline dynamically
3. Compares predictions against ground-truth targets
4. Calculates metrics:
   - Affordability Status Accuracy
   - Recommended Payment Method Accuracy
   - Amount Safe to Pay MAE / Match Rate
   - Earliest Date Match Rate
   - Payment Plan Match Rate
   - Spending Changes Match Rate
5. Reports per-request discrepancies and summary statistics without hardcoded labels.
"""

import sys
import os
import argparse
import datetime
from typing import Dict, Any, List
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.data_loader import load_all_data, load_dataset_file
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


class SampleEvaluator:
    """Evaluates pipeline predictions against ground-truth sample requests."""

    def __init__(self, data_dir: str = 'dataset', use_rag: bool = True):
        self.data_dir = os.path.abspath(data_dir)
        self.samples_path = os.path.join(self.data_dir, 'sample_requests.csv')
        self.use_rag = use_rag

    def run_evaluation(self, verbose: bool = True) -> Dict[str, Any]:
        """Runs prediction on sample requests and calculates comprehensive evaluation metrics."""
        if not os.path.exists(self.samples_path):
            raise FileNotFoundError(f"Sample requests file not found: {self.samples_path}")

        df_samples = pd.read_csv(self.samples_path)
        total_samples = len(df_samples)

        if total_samples == 0:
            return {'error': 'No samples found'}

        # 1. Load supporting data
        raw_data = load_all_data(self.data_dir)
        clean_data = clean_all_data(raw_data)

        # 2. Initialize pipeline components
        joiner = DataJoiner(clean_data)
        img_extractor = ImageExtractor()
        msg_parser = MessageParser()
        curr_converter = CurrencyConverter(clean_data['exchange_rates'])
        reconstructor = EventReconstructor(img_extractor, msg_parser, curr_converter)
        forecast_engine = ForecastEngine(forecast_days=90, conservative_buffer=1.0)
        plan_engine = PaymentPlanEngine()
        decision_engine = DecisionEngine(forecast_engine, plan_engine)

        rag_pipeline = None
        if self.use_rag:
            try:
                k_dir = os.path.join(PROJECT_ROOT, 'knowledge')
                idx_file = os.path.join(k_dir, 'index.json')
                rag_pipeline = RAGPipeline(knowledge_dir=k_dir, index_path=idx_file, enabled=True)
                rag_pipeline.build_index(force_rebuild=False)
            except Exception:
                rag_pipeline = None

        explanation_gen = ExplanationGenerator(rag_pipeline=rag_pipeline)

        results = []
        status_matches = 0
        method_matches = 0
        safe_amt_diffs = []
        date_matches = 0
        plan_matches = 0
        changes_matches = 0

        for idx, row in df_samples.iterrows():
            req_id = str(row['request_id'])
            
            # Fetch request context and evaluate
            ctx = joiner.get_request_context(req_id)
            recon = reconstructor.reconstruct(ctx)
            decision = decision_engine.evaluate(ctx, recon)
            explanation = explanation_gen.generate(ctx, decision)

            # Predicted values
            p_status = decision.affordability_status
            p_method = decision.recommended_payment_method
            p_safe = float(decision.amount_safe_to_pay)
            p_plan = str(decision.payment_plan)
            p_date = str(decision.earliest_date_for_full_payment) if decision.earliest_date_for_full_payment else ""
            p_changes = str(decision.spending_changes_needed)

            # Ground truth values
            gt_status = str(row.get('affordability_status', ''))
            gt_method = str(row.get('recommended_payment_method', ''))
            gt_safe = float(row.get('amount_safe_to_pay', 0.0))
            gt_plan = str(row.get('payment_plan', ''))
            gt_date = str(row.get('earliest_date_for_full_payment', '')) if pd.notna(row.get('earliest_date_for_full_payment')) else ""
            gt_changes = str(row.get('spending_changes_needed', ''))

            # Comparison
            m_status = (p_status == gt_status)
            m_method = (p_method == gt_method)
            diff_safe = abs(p_safe - gt_safe)
            m_safe = (diff_safe < 0.01)
            m_date = (p_date == gt_date)
            m_plan = (p_plan == gt_plan)
            m_changes = (p_changes == gt_changes)

            if m_status: status_matches += 1
            if m_method: method_matches += 1
            safe_amt_diffs.append(diff_safe)
            if m_date: date_matches += 1
            if m_plan: plan_matches += 1
            if m_changes: changes_matches += 1

            results.append({
                'request_id': req_id,
                'status_pred': p_status,
                'status_gt': gt_status,
                'status_match': m_status,
                'method_pred': p_method,
                'method_gt': gt_method,
                'method_match': m_method,
                'safe_amt_pred': p_safe,
                'safe_amt_gt': gt_safe,
                'safe_amt_diff': diff_safe,
                'date_pred': p_date,
                'date_gt': gt_date,
                'date_match': m_date,
                'plan_pred': p_plan,
                'plan_gt': gt_plan,
                'plan_match': m_plan,
                'changes_pred': p_changes,
                'changes_gt': gt_changes,
                'changes_match': m_changes,
                'explanation': explanation
            })

        # Calculate metrics
        status_acc = status_matches / total_samples
        method_acc = method_matches / total_samples
        safe_mae = float(np.mean(safe_amt_diffs))
        safe_match_rate = sum(1 for d in safe_amt_diffs if d < 0.01) / total_samples
        date_acc = date_matches / total_samples
        plan_acc = plan_matches / total_samples
        changes_acc = changes_matches / total_samples

        metrics = {
            'total_samples': total_samples,
            'status_accuracy': status_acc,
            'method_accuracy': method_acc,
            'safe_amount_mae': safe_mae,
            'safe_amount_exact_match_rate': safe_match_rate,
            'earliest_date_accuracy': date_acc,
            'payment_plan_accuracy': plan_acc,
            'spending_changes_accuracy': changes_acc,
            'results': results
        }

        if verbose:
            self._print_report(metrics)

        return metrics

    def _print_report(self, m: Dict[str, Any]):
        """Prints a well-formatted summary of evaluation metrics."""
        print("=" * 80)
        print("           BUY OR WAIT? — VALIDATION SAMPLES EVALUATION REPORT")
        print("=" * 80)
        print(f"Total Validation Samples Evaluated: {m['total_samples']}")
        print("-" * 80)
        print(f"Affordability Status Accuracy:       {m['status_accuracy'] * 100:6.2f}% ({int(m['status_accuracy'] * m['total_samples'])}/{m['total_samples']})")
        print(f"Recommended Payment Method Accuracy: {m['method_accuracy'] * 100:6.2f}% ({int(m['method_accuracy'] * m['total_samples'])}/{m['total_samples']})")
        print(f"Amount Safe to Pay MAE:              {m['safe_amount_mae']:6.2f}")
        print(f"Amount Safe to Pay Exact Match Rate: {m['safe_amount_exact_match_rate'] * 100:6.2f}%")
        print(f"Earliest Safe Date Accuracy:         {m['earliest_date_accuracy'] * 100:6.2f}%")
        print(f"Payment Plan Match Rate:             {m['payment_plan_accuracy'] * 100:6.2f}%")
        print(f"Spending Changes Match Rate:         {m['spending_changes_accuracy'] * 100:6.2f}%")
        print("-" * 80)
        print("Per-Request Breakdown (Sample mismatches highlighted):")
        for r in m['results']:
            mismatches = []
            if not r['status_match']: mismatches.append(f"status({r['status_pred']} != {r['status_gt']})")
            if not r['method_match']: mismatches.append(f"method({r['method_pred']} != {r['method_gt']})")
            if r['safe_amt_diff'] >= 0.01: mismatches.append(f"safe_amt({r['safe_amt_pred']:.2f} != {r['safe_amt_gt']:.2f})")
            if not r['plan_match']: mismatches.append("plan")
            if not r['date_match']: mismatches.append(f"date({r['date_pred']} != {r['date_gt']})")

            tag = "PASS" if not mismatches else f"DIFF: {', '.join(mismatches)}"
            print(f"  [{r['request_id']}] {tag}")
        print("=" * 80)


if __name__ == '__main__':
    evaluator = SampleEvaluator()
    evaluator.run_evaluation(verbose=True)
