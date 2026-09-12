"""
Data Cleaner Module

Performs type casting, whitespace stripping, date standardization,
pipe-delimited parsing, and schema sanitization across all datasets.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import Dict, List, Set, Optional, Any
import pandas as pd
import numpy as np


def _clean_str_series(series: pd.Series) -> pd.Series:
    """Strips leading/trailing whitespace and converts empty strings to NaN."""
    return series.astype(str).str.strip().replace({'': np.nan, 'nan': np.nan, 'None': np.nan})


def _parse_pipe_list(val: Any) -> List[str]:
    """Parses a pipe-delimited string into a list of non-empty stripped strings."""
    if pd.isna(val) or val is None:
        return []
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ('none', 'nan'):
        return []
    return [item.strip() for item in val_str.split('|') if item.strip()]


def clean_financial_profiles(df: pd.DataFrame) -> pd.DataFrame:
    clean_df = df.copy()
    clean_df['user_id'] = _clean_str_series(clean_df['user_id'])
    clean_df['home_currency'] = _clean_str_series(clean_df['home_currency']).str.upper()
    clean_df['current_available_balance'] = pd.to_numeric(clean_df['current_available_balance'], errors='raise').astype(float)
    clean_df['minimum_balance_to_keep'] = pd.to_numeric(clean_df['minimum_balance_to_keep'], errors='raise').astype(float)
    
    clean_df['financial_priorities_list'] = clean_df['financial_priorities'].apply(_parse_pipe_list)
    clean_df['expense_categories_to_protect_list'] = clean_df['expense_categories_to_protect'].apply(_parse_pipe_list)
    clean_df['expense_categories_user_is_willing_to_reduce_list'] = clean_df['expense_categories_user_is_willing_to_reduce'].apply(_parse_pipe_list)
    clean_df['expense_categories_user_is_willing_to_stop_list'] = clean_df['expense_categories_user_is_willing_to_stop'].apply(_parse_pipe_list)
    clean_df['payment_methods_user_will_consider_list'] = clean_df['payment_methods_user_will_consider'].apply(_parse_pipe_list)
    
    clean_df['max_installment_months'] = pd.to_numeric(clean_df['max_installment_months'], errors='coerce')
    return clean_df


def clean_requests(df: pd.DataFrame) -> pd.DataFrame:
    clean_df = df.copy()
    clean_df['request_id'] = _clean_str_series(clean_df['request_id'])
    clean_df['user_id'] = _clean_str_series(clean_df['user_id'])
    clean_df['request_date'] = pd.to_datetime(clean_df['request_date'], errors='raise').dt.strftime('%Y-%m-%d')
    clean_df['request_type'] = _clean_str_series(clean_df['request_type']).str.lower()
    clean_df['requested_amount'] = pd.to_numeric(clean_df['requested_amount'], errors='raise').astype(float)
    clean_df['desired_completion_date'] = pd.to_datetime(clean_df['desired_completion_date'], errors='raise').dt.strftime('%Y-%m-%d')
    clean_df['allows_partial_payment'] = clean_df['allows_partial_payment'].astype(bool)
    clean_df['request_text'] = _clean_str_series(clean_df['request_text'])
    return clean_df


def clean_financial_events(df: pd.DataFrame) -> pd.DataFrame:
    clean_df = df.copy()
    clean_df['event_id'] = _clean_str_series(clean_df['event_id'])
    clean_df['user_id'] = _clean_str_series(clean_df['user_id'])
    clean_df['event_type'] = _clean_str_series(clean_df['event_type']).str.lower()
    clean_df['description'] = _clean_str_series(clean_df['description'])
    clean_df['category'] = _clean_str_series(clean_df['category']).str.lower()
    clean_df['direction'] = _clean_str_series(clean_df['direction']).str.lower()
    clean_df['amount'] = pd.to_numeric(clean_df['amount'], errors='coerce')
    clean_df['currency'] = _clean_str_series(clean_df['currency']).str.upper()
    clean_df['event_date'] = pd.to_datetime(clean_df['event_date'], errors='raise').dt.strftime('%Y-%m-%d')
    clean_df['settlement_date'] = pd.to_datetime(clean_df['settlement_date'], errors='coerce').dt.strftime('%Y-%m-%d')
    clean_df['status'] = _clean_str_series(clean_df['status']).str.lower()
    clean_df['linked_event_id'] = _clean_str_series(clean_df['linked_event_id'])
    clean_df['flexibility'] = _clean_str_series(clean_df['flexibility']).str.lower()
    clean_df['minimum_allowed_amount'] = pd.to_numeric(clean_df['minimum_allowed_amount'], errors='coerce')
    return clean_df


def clean_exchange_rates(df: pd.DataFrame) -> pd.DataFrame:
    clean_df = df.copy()
    clean_df['rate_date'] = pd.to_datetime(clean_df['rate_date'], errors='raise').dt.strftime('%Y-%m-%d')
    clean_df['from_currency'] = _clean_str_series(clean_df['from_currency']).str.upper()
    clean_df['to_currency'] = _clean_str_series(clean_df['to_currency']).str.upper()
    clean_df['rate'] = pd.to_numeric(clean_df['rate'], errors='raise').astype(float)
    return clean_df


def clean_request_payment_options(df: pd.DataFrame) -> pd.DataFrame:
    clean_df = df.copy()
    clean_df['payment_option_id'] = _clean_str_series(clean_df['payment_option_id'])
    clean_df['request_id'] = _clean_str_series(clean_df['request_id'])
    clean_df['payment_method'] = _clean_str_series(clean_df['payment_method']).str.lower()
    clean_df['payment_amount'] = pd.to_numeric(clean_df['payment_amount'], errors='raise').astype(float)
    clean_df['number_of_payments'] = pd.to_numeric(clean_df['number_of_payments'], errors='raise').astype(int)
    clean_df['first_payment_date'] = pd.to_datetime(clean_df['first_payment_date'], errors='raise').dt.strftime('%Y-%m-%d')
    clean_df['payment_frequency_days'] = pd.to_numeric(clean_df['payment_frequency_days'], errors='coerce')
    clean_df['financing_fee'] = pd.to_numeric(clean_df['financing_fee'], errors='raise').astype(float)
    clean_df['total_payable_amount'] = pd.to_numeric(clean_df['total_payable_amount'], errors='raise').astype(float)
    return clean_df


def clean_messages(df: pd.DataFrame) -> pd.DataFrame:
    clean_df = df.copy()
    clean_df['message_id'] = _clean_str_series(clean_df['message_id'])
    clean_df['user_id'] = _clean_str_series(clean_df['user_id'])
    clean_df['request_id'] = _clean_str_series(clean_df['request_id'])
    clean_df['related_event_id'] = _clean_str_series(clean_df['related_event_id'])
    clean_df['sent_at'] = pd.to_datetime(clean_df['sent_at'], errors='raise')
    clean_df['source_type'] = _clean_str_series(clean_df['source_type']).str.lower()
    clean_df['message_text'] = _clean_str_series(clean_df['message_text'])
    return clean_df


def clean_images(df: pd.DataFrame) -> pd.DataFrame:
    clean_df = df.copy()
    clean_df['image_id'] = _clean_str_series(clean_df['image_id'])
    clean_df['user_id'] = _clean_str_series(clean_df['user_id'])
    clean_df['request_id'] = _clean_str_series(clean_df['request_id'])
    clean_df['related_event_id'] = _clean_str_series(clean_df['related_event_id'])
    return clean_df


def clean_all_data(raw_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Applies cleaning and type validation across all raw datasets."""
    cleaned = {}
    if 'financial_profiles' in raw_data:
        cleaned['financial_profiles'] = clean_financial_profiles(raw_data['financial_profiles'])
    if 'requests' in raw_data:
        cleaned['requests'] = clean_requests(raw_data['requests'])
    if 'sample_requests' in raw_data:
        cleaned['sample_requests'] = clean_requests(raw_data['sample_requests'])
        for col in ['amount_safe_to_pay', 'affordability_status', 'recommended_payment_method',
                    'payment_plan', 'earliest_date_for_full_payment', 'spending_changes_needed',
                    'decision_explanation']:
            if col in raw_data['sample_requests'].columns:
                cleaned['sample_requests'][col] = raw_data['sample_requests'][col]
    if 'financial_events' in raw_data:
        cleaned['financial_events'] = clean_financial_events(raw_data['financial_events'])
    if 'exchange_rates' in raw_data:
        cleaned['exchange_rates'] = clean_exchange_rates(raw_data['exchange_rates'])
    if 'request_payment_options' in raw_data:
        cleaned['request_payment_options'] = clean_request_payment_options(raw_data['request_payment_options'])
    if 'messages' in raw_data:
        cleaned['messages'] = clean_messages(raw_data['messages'])
    if 'images' in raw_data:
        cleaned['images'] = clean_images(raw_data['images'])
    if 'output_template' in raw_data:
        cleaned['output_template'] = raw_data['output_template'].copy()
    return cleaned


if __name__ == '__main__':
    from src.data_loader import load_all_data
    print('Testing data_cleaner.py...')
    raw = load_all_data()
    clean = clean_all_data(raw)
    for name, df in clean.items():
        print(f'Cleaned {name:25s}: {df.shape[0]:6d} rows, {df.shape[1]:2d} cols')
    print('Data cleaning test passed successfully!')
