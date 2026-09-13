"""
Main Execution Script — Buy or Wait? Financial Affordability System

Runs the full 16-stage pipeline end-to-end:
1. Load dataset
2. Clean & normalize data
3. Join user contexts
4. Image receipt extraction
5. Message processing & prompt injection defense
6. Currency normalization
7. Event reconstruction
8. 90-day cash flow simulation
9. Payment plan generation & ranking
10. Explanation generation
11. Output validation
12. Generate output.csv
"""

import sys
import os
import time
import datetime
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
from src.validator import OutputValidator
from src.output_writer import OutputWriter
from src.rag.rag_pipeline import RAGPipeline


def run_pipeline(data_dir: str = 'dataset', output_path: str = 'output.csv', use_rag: bool = True) -> pd.DataFrame:
    start_time = time.time()
    print("=" * 70)
    print("BUY OR WAIT? — FINANCIAL AFFORDABILITY DECISION SYSTEM")
    print(f"Start Time: {datetime.datetime.now().isoformat()}")
    print("=" * 70)

    # Resolve dataset directory if invoked from a subfolder
    if not os.path.exists(data_dir):
        for candidate in [
            os.path.join('..', data_dir),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dataset'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dataset')
        ]:
            if os.path.exists(candidate):
                data_dir = candidate
                break

    # 1. Load Data
    print(f"\n[Stage 2] Loading dataset from '{data_dir}'...")
    raw_data = load_all_data(data_dir)
    print(f"Loaded {len(raw_data['requests'])} evaluation requests, {len(raw_data['financial_profiles'])} profiles, {len(raw_data['financial_events'])} events.")

    # 2. Clean Data
    print("\n[Stage 3] Cleaning and normalizing data...")
    clean_data = clean_all_data(raw_data)

    # 3. Initialize Engine Components
    print("\n[Stage 4-13] Initializing pipeline components...")
    joiner = DataJoiner(clean_data)
    img_extractor = ImageExtractor()
    msg_parser = MessageParser()
    curr_converter = CurrencyConverter(clean_data['exchange_rates'])
    reconstructor = EventReconstructor(img_extractor, msg_parser, curr_converter)
    forecast_engine = ForecastEngine(forecast_days=90, conservative_buffer=1.0)
    plan_engine = PaymentPlanEngine()
    decision_engine = DecisionEngine(forecast_engine, plan_engine)

    # Initialize RAG Pipeline
    rag_pipeline = None
    if use_rag:
        print("\n[RAG Subsystem] Initializing RAG Knowledge Base and Vector Index...")
        try:
            k_dir = 'knowledge'
            if not os.path.exists(k_dir):
                for cand in [
                    '../knowledge',
                    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'knowledge'),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'knowledge')
                ]:
                    if os.path.exists(cand):
                        k_dir = cand
                        break
            
            idx_file = os.path.join(k_dir, 'index.json')
            rag_pipeline = RAGPipeline(knowledge_dir=k_dir, index_path=idx_file, enabled=True)
            chunk_count = rag_pipeline.build_index(force_rebuild=False)
            print(f"  RAG Vector Store ready: {chunk_count} knowledge chunks indexed from '{k_dir}'.")
        except Exception as e:
            print(f"  Warning: RAG initialization failed ({e}). Proceeding with deterministic fallback.")
            rag_pipeline = None

    explanation_gen = ExplanationGenerator(rag_pipeline=rag_pipeline)
    validator = OutputValidator(joiner)
    writer = OutputWriter()

    # 4. Process Evaluation Requests
    requests_df = clean_data['requests']
    total_requests = len(requests_df)
    print(f"\n[Stage 10-13] Evaluating {total_requests} financial requests...")

    output_records = []
    for idx, row in requests_df.iterrows():
        req_id = str(row['request_id'])
        ctx = joiner.get_request_context(req_id)
        recon = reconstructor.reconstruct(ctx)
        decision = decision_engine.evaluate(ctx, recon)
        explanation = explanation_gen.generate(ctx, decision)

        output_records.append({
            'request_id': req_id,
            'amount_safe_to_pay': decision.amount_safe_to_pay,
            'affordability_status': decision.affordability_status,
            'recommended_payment_method': decision.recommended_payment_method,
            'payment_plan': decision.payment_plan,
            'earliest_date_for_full_payment': decision.earliest_date_for_full_payment,
            'spending_changes_needed': decision.spending_changes_needed,
            'decision_explanation': explanation
        })

        if (idx + 1) % 50 == 0 or (idx + 1) == total_requests:
            print(f"  Processed {idx + 1}/{total_requests} requests ({(idx + 1) / total_requests * 100:.1f}%)")

    # 5. Format DataFrame
    df_output = pd.DataFrame(output_records)

    # 6. Validate Output
    print("\n[Stage 14] Running validation checklist...")
    issues = validator.validate_dataframe(df_output, expected_count=total_requests)
    error_issues = [i for i in issues if i.severity == 'ERROR']
    warning_issues = [i for i in issues if i.severity == 'WARNING']

    if error_issues:
        print(f"Validation FAILED with {len(error_issues)} errors:")
        for err in error_issues[:10]:
            print(f"  ERROR [{err.request_id}] {err.column}: {err.message}")
        raise ValueError(f"Output validation failed with {len(error_issues)} errors.")
    else:
        print(f"Validation PASSED! 0 errors across {total_requests} rows.")
        if warning_issues:
            print(f"  ({len(warning_issues)} non-fatal warnings logged)")

    # 7. Write Output Files
    print(f"\n[Stage 16] Writing output files...")
    target_locations = [
        output_path
    ]

    for loc in target_locations:
        try:
            writer.write_csv(output_records, loc)
            print(f"  Wrote {len(df_output)} predictions to: {os.path.abspath(loc)}")
        except Exception as e:
            if loc == output_path:
                raise
    # 8. Supabase Cloud Sync & Telemetry
    try:
        from src.supabase_client import get_supabase_adapter
        supabase = get_supabase_adapter()
        if supabase.is_available:
            print("\n[Supabase Integration] Syncing predictions and run telemetry to Supabase cloud...")
            synced = supabase.sync_predictions(df_output)
            print(f"  Synced {synced} prediction rows to Supabase.")
            supabase.log_run(
                run_name="Full Dataset Evaluation",
                total_requests=total_requests,
                metrics={
                    "execution_time_seconds": round(time.time() - start_time, 2),
                    "status_distribution": df_output['affordability_status'].value_counts().to_dict(),
                    "method_distribution": df_output['recommended_payment_method'].value_counts().to_dict()
                }
            )
    except Exception as e:
        print(f"  Note: Supabase sync skipped: {e}")

    # 9. Report Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 70)
    print(f"Total Requests Processed: {total_requests}")
    print(f"Execution Time: {elapsed:.2f} seconds ({elapsed / total_requests * 1000:.1f} ms/req)")
    print("\nAffordability Status Distribution:")
    print(df_output['affordability_status'].value_counts().to_string())
    print("\nRecommended Payment Method Distribution:")
    print(df_output['recommended_payment_method'].value_counts().to_string())
    print("=" * 70)
    return df_output

def main(use_rag: bool = True):
    return run_pipeline(use_rag=use_rag)


if __name__ == '__main__':
    main()
