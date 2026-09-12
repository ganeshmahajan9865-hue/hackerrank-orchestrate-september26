import sys, os
sys.path.insert(0, '.')
import pandas as pd
import numpy as np

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

raw = load_all_data()
clean = clean_all_data(raw)
joiner = DataJoiner(clean)
img_ext = ImageExtractor()
msg_parse = MessageParser()
curr_conv = CurrencyConverter(clean['exchange_rates'])
reconstructor = EventReconstructor(img_ext, msg_parse, curr_conv)
forecast = ForecastEngine()
plan_engine = PaymentPlanEngine()
decision_engine = DecisionEngine(forecast, plan_engine)
samples = clean['sample_requests']

print(f"{'Req ID':<10} {'Afford Status':<22} {'Method':<18} {'Earliest':<12} {'Changes':<25} {'Plan Match':<10}")

total_samples = len(samples)
matches = {
    'status': 0,
    'method': 0,
    'earliest': 0,
    'changes': 0,
    'plan': 0
}

for _, row in samples.iterrows():
    req_id = row['request_id']
    ctx = joiner.get_request_context(req_id)
    recon = reconstructor.reconstruct(ctx)
    res = decision_engine.evaluate(ctx, recon)
    
    gt_status = row['affordability_status']
    gt_method = row['recommended_payment_method']
    gt_earliest = row['earliest_date_for_full_payment']
    gt_changes = row['spending_changes_needed']
    gt_plan = row['payment_plan']
    
    status_match = (res.affordability_status == gt_status)
    method_match = (res.recommended_payment_method == gt_method)
    earliest_match = (str(res.earliest_date_for_full_payment) == str(gt_earliest)) or (pd.isna(res.earliest_date_for_full_payment) and pd.isna(gt_earliest))
    changes_match = (res.spending_changes_needed == gt_changes)
    plan_match = (res.payment_plan == gt_plan)
    
    if status_match: matches['status'] += 1
    if method_match: matches['method'] += 1
    if earliest_match: matches['earliest'] += 1
    if changes_match: matches['changes'] += 1
    if plan_match: matches['plan'] += 1
    
    flag = "OK" if (status_match and method_match and plan_match) else "DIFF"
    print(f"{req_id:<10} {res.affordability_status:<22} (GT:{gt_status}) {flag}")

print("\nAccuracy Breakdown:")
for k, v in matches.items():
    print(f"  {k}: {v}/{total_samples} ({v/total_samples*100:.1f}%)")
