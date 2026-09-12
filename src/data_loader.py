import os
from typing import Dict, Optional
import pandas as pd

EXPECTED_COLUMNS: Dict[str, list] = {
    'requests': [
        'request_id', 'user_id', 'request_date', 'request_type',
        'requested_amount', 'desired_completion_date', 'allows_partial_payment',
        'request_text'
    ],
    'sample_requests': [
        'request_id', 'user_id', 'request_date', 'request_type',
        'requested_amount', 'desired_completion_date', 'allows_partial_payment',
        'request_text', 'amount_safe_to_pay', 'affordability_status',
        'recommended_payment_method', 'payment_plan',
        'earliest_date_for_full_payment', 'spending_changes_needed',
        'decision_explanation'
    ],
    'financial_profiles': [
       'user_id', 'home_currency', 'current_available_balance',
        'minimum_balance_to_keep', 'financial_priorities',
        'expense_categories_to_protect',
        'expense_categories_user_is_willing_to_reduce',
        'expense_categories_user_is_willing_to_stop',
        'payment_methods_user_will_consider', 'max_installment_months'
    ],
    'financial_events': [
        'event_id', 'user_id', 'event_type', 'description', 'category',
        'direction', 'amount', 'currency', 'event_date', 'settlement_date',
        'status', 'linked_event_id', 'flexibility', 'minimum_allowed_amount'
    ],
    'exchange_rates': [
        'rate_date', 'from_currency', 'to_currency', 'rate'
    ],
    'request_payment_options': [
        'payment_option_id', 'request_id', 'payment_method', 'payment_amount',
        'number_of_payments', 'first_payment_date', 'payment_frequency_days',
        'financing_fee', 'total_payable_amount'
    ],
    'messages': [
        'message_id', 'user_id', 'request_id', 'related_event_id', 'sent_at',
        'source_type', 'message_text'
    ],
    'images': [
        'image_id', 'user_id', 'request_id', 'related_event_id'
    ]
}


def resolve_dataset_path(dataset_dir: Optional[str] = None) -> str:
    """Resolves the dataset directory path whether run from root or a subfolder."""
    if dataset_dir is not None:
        if os.path.isdir(dataset_dir):
            return os.path.abspath(dataset_dir)
        raise FileNotFoundError(f'Explicit dataset directory not found: {dataset_dir}')
    
    # Try current directory / dataset
    if os.path.isdir('dataset'):
        return os.path.abspath('dataset')
    
    # Try parent directory / dataset
    parent_dataset = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dataset')
    if os.path.isdir(parent_dataset):
        return os.path.abspath(parent_dataset)
    
    raise FileNotFoundError('Could not locate dataset directory.')


def load_dataset_file(file_name: str, dataset_dir: Optional[str] = None) -> pd.DataFrame:
    """Loads a single CSV file from the dataset directory and validates columns."""
    base_dir = resolve_dataset_path(dataset_dir)
    file_path = os.path.join(base_dir, f'{file_name}.csv')
    
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f'Required dataset file not found: {file_path}')
    
    df = pd.read_csv(file_path)
    
    if file_name in EXPECTED_COLUMNS:
        expected = EXPECTED_COLUMNS[file_name]
        missing = [col for col in expected if col not in df.columns]
        if missing:
            raise ValueError(f'File {file_name}.csv is missing required columns: {missing}')
            
    return df


def load_all_data(dataset_dir: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """Loads all required dataset CSVs into a dictionary of DataFrames."""
    base_dir = resolve_dataset_path(dataset_dir)
    data = {}
    
    for key in EXPECTED_COLUMNS:
        data[key] = load_dataset_file(key, base_dir)
        
    # Also load template output.csv if present
    output_path = os.path.join(base_dir, 'output.csv')
    if os.path.isfile(output_path):
        data['output_template'] = pd.read_csv(output_path)
        
    return data


if __name__ == '__main__':
    print('Testing data_loader.py...')
    data = load_all_data()
    for name, df in data.items():
        print(f'Loaded {name:25s}: {df.shape[0]:6d} rows, {df.shape[1]:2d} cols')
    print('Data loading test passed successfully!')
