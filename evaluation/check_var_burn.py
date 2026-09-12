import sys, os
sys.path.insert(0, '.')
import pandas as pd
from src.data_loader import load_all_data
from src.data_cleaner import clean_all_data
from src.data_joiner import DataJoiner

raw = load_all_data()
clean = clean_all_data(raw)
joiner = DataJoiner(clean)

FIXED_COMMITMENT_CATEGORIES = {
    'rent', 'housing', 'utilities', 'insurance', 'education', 
    'debt_repayment', 'family_support', 'cloud_storage', 
    'delivery_membership', 'gym', 'music_subscription', 'streaming',
    'healthcare', 'entertainment'
}

for req_id in ['request_06', 'request_11', 'request_21']:
    ctx = joiner.get_request_context(req_id)
    evs = ctx.events
    settled_debits = evs[(evs['direction'] == 'debit') & (evs['status'] == 'settled') & (evs['event_date'] <= ctx.request_date)]
    var_debits = settled_debits[~settled_debits['category'].isin(FIXED_COMMITMENT_CATEGORIES)]
    min_d = pd.to_datetime(settled_debits['event_date'].min())
    max_d = pd.to_datetime(settled_debits['event_date'].max())
    days = (max_d - min_d).days
    burn = var_debits['amount'].sum() / days if days > 0 else 0
    print(f"{req_id}: var burn rate = {burn:.2f}/day across {days} days")
