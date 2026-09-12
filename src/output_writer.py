"""
Output Writer Module

Writes validated predictions to output.csv matching the exact competition contract:
request_id,amount_safe_to_pay,affordability_status,recommended_payment_method,payment_plan,earliest_date_for_full_payment,spending_changes_needed,decision_explanation
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import List, Dict, Any
import pandas as pd


OUTPUT_COLUMNS = [
    'request_id',
    'amount_safe_to_pay',
    'affordability_status',
    'recommended_payment_method',
    'payment_plan',
    'earliest_date_for_full_payment',
    'spending_changes_needed',
    'decision_explanation'
]


class OutputWriter:
    """Formats and writes decision records to output CSV files."""

    def __init__(self):
        pass

    def write_csv(self, records: List[Dict[str, Any]], target_path: str) -> pd.DataFrame:
        """Formats and saves predictions to the specified path."""
        formatted_rows = []
        for r in records:
            earliest_val = r.get('earliest_date_for_full_payment')
            if earliest_val is None or pd.isna(earliest_val) or str(earliest_val).lower() == 'nan':
                earliest_str = ''
            else:
                earliest_str = str(earliest_val)

            row = {
                'request_id': str(r['request_id']),
                'amount_safe_to_pay': round(float(r['amount_safe_to_pay']), 2),
                'affordability_status': str(r['affordability_status']),
                'recommended_payment_method': str(r['recommended_payment_method']),
                'payment_plan': str(r['payment_plan']),
                'earliest_date_for_full_payment': earliest_str,
                'spending_changes_needed': str(r['spending_changes_needed']),
                'decision_explanation': str(r['decision_explanation'])
            }
            formatted_rows.append(row)

        df = pd.DataFrame(formatted_rows, columns=OUTPUT_COLUMNS)
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        df.to_csv(target_path, index=False, encoding='utf-8')
        return df
