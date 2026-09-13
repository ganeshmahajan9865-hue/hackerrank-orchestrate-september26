"""
Script to verify mathematical invariance across all 250 evaluation requests:
Runs pipeline with RAG enabled vs RAG disabled and asserts 100% equivalence on all financial fields.
"""

import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import run_pipeline


def main():
    print("=" * 70)
    print("RUNNING RAG EQUIVALENCE VERIFICATION (250 REQUESTS)")
    print("=" * 70)

    # 1. Run with RAG Enabled
    print("\n--- Running with RAG ENABLED ---")
    df_rag = run_pipeline(data_dir='dataset', output_path='output_rag.csv', use_rag=True)

    # 2. Run with RAG Disabled
    print("\n--- Running with RAG DISABLED ---")
    df_norag = run_pipeline(data_dir='dataset', output_path='output_norag.csv', use_rag=False)

    print("\n" + "=" * 70)
    print("VERIFYING FIELD-BY-FIELD INVARIANCE")
    print("=" * 70)

    if df_rag is None and os.path.exists('output_rag.csv'):
        df_rag = pd.read_csv('output_rag.csv')
    if df_norag is None and os.path.exists('output_norag.csv'):
        df_norag = pd.read_csv('output_norag.csv')

    assert len(df_rag) == len(df_norag) == 250, f"Expected 250 rows, got {len(df_rag)} vs {len(df_norag)}"

    financial_columns = [
        'request_id',
        'amount_safe_to_pay',
        'affordability_status',
        'recommended_payment_method',
        'payment_plan',
        'earliest_date_for_full_payment',
        'spending_changes_needed'
    ]

    mismatches = {col: 0 for col in financial_columns}
    for idx in range(len(df_rag)):
        r1 = df_rag.iloc[idx]
        r2 = df_norag.iloc[idx]

        for col in financial_columns:
            val1 = r1[col]
            val2 = r2[col]
            
            # Handle NaN / None equality
            if (pd.isna(val1) or val1 == '' or str(val1).lower() == 'nan') and \
               (pd.isna(val2) or val2 == '' or str(val2).lower() == 'nan'):
                continue
            
            if col == 'amount_safe_to_pay':
                if not np.isclose(float(val1), float(val2), atol=1e-2):
                    mismatches[col] += 1
            else:
                if str(val1).strip() != str(val2).strip():
                    mismatches[col] += 1

    print("Field Invariance Check Results:")
    all_passed = True
    for col, count in mismatches.items():
        status = "PASSED (0 mismatches)" if count == 0 else f"FAILED ({count} mismatches)"
        print(f"  {col:32}: {status}")
        if count > 0:
            all_passed = False

    assert all_passed, "Financial invariance assertion failed!"
    print("\nSUCCESS: All financial decisions, amounts, and plans are 100.0% IDENTICAL!")

    # Check explanation enhancement
    different_explanations = 0
    for idx in range(len(df_rag)):
        e1 = df_rag.iloc[idx]['decision_explanation']
        e2 = df_norag.iloc[idx]['decision_explanation']
        if e1 != e2:
            different_explanations += 1

    print(f"Explanations enhanced by RAG: {different_explanations}/{len(df_rag)} ({different_explanations/len(df_rag)*100:.1f}%)")

    # Clean up temporary verification files
    for temp_f in ['output_rag.csv', 'output_norag.csv']:
        if os.path.exists(temp_f):
            try:
                os.remove(temp_f)
            except Exception:
                pass


if __name__ == '__main__':
    main()
