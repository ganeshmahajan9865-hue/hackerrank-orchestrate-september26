import sys, os
sys.path.insert(0, '.')
import pandas as pd
from src.data_loader import load_all_data
raw = load_all_data()
samples = raw['sample_requests']
options = raw['request_payment_options']
profiles = raw['financial_profiles']

for req_id in ['request_02', 'request_07', 'request_12', 'request_17', 'request_22']:
    s = samples[samples['request_id'] == req_id].iloc[0]
    p = profiles[profiles['user_id'] == s['user_id']].iloc[0]
    print(f"=== {req_id} ({s['user_id']}) ===")
    print(f"User max_months: {p['max_installment_months']}, consider: {p['payment_methods_user_will_consider']}")
    opts = options[options['request_id'] == req_id]
    for _, opt in opts.iterrows():
        print(f"  {opt['payment_option_id']}: method={opt['payment_method']}, num={opt['number_of_payments']}, freq={opt['payment_frequency_days']}, total={opt['total_payable_amount']}, 1st={opt['first_payment_date']}")
    print(f"  GT Chosen: {s['recommended_payment_method']}, Plan: {s['payment_plan']}\n")
