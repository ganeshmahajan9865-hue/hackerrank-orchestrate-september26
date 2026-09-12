import sys, os
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
from src.data_loader import load_all_data
from src.data_cleaner import clean_all_data
from src.data_joiner import DataJoiner

raw = load_all_data()
clean = clean_all_data(raw)
joiner = DataJoiner(clean)
samples = clean['sample_requests']

print(f"{'Req ID':<10} {'Req Amt':>12} {'Curr Bal':>12} {'Min Bal':>10} {'Headroom':>12} {'GT Safe':>12} {'Diff (Headroom - Safe)':>22}")
for _, row in samples.iterrows():
    ctx = joiner.get_request_context(row['request_id'])
    curr_bal = ctx.profile.current_available_balance
    min_bal = ctx.profile.minimum_balance_to_keep
    headroom = curr_bal - min_bal
    gt_safe = row['amount_safe_to_pay']
    diff = headroom - gt_safe
    print(f"{row['request_id']:<10} {row['requested_amount']:>12,.2f} {curr_bal:>12,.2f} {min_bal:>10,.2f} {headroom:>12,.2f} {gt_safe:>12,.2f} {diff:>22,.2f}")
