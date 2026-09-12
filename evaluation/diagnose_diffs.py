import sys, os
sys.path.insert(0, '.')
import pandas as pd

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

for req_id in ['request_03', 'request_05', 'request_06', 'request_11', 'request_18', 'request_19', 'request_21']:
    ctx = joiner.get_request_context(req_id)
    recon = reconstructor.reconstruct(ctx)
    res = decision_engine.evaluate(ctx, recon)
    gt = samples[samples['request_id'] == req_id].iloc[0]
    
    print(f"=== {req_id} ===")
    print(f"  Req Date: {ctx.request_date}, Desired: {ctx.desired_completion_date}, Req Amt: {ctx.requested_amount}")
    print(f"  Curr Bal: {ctx.profile.current_available_balance}, Min Bal: {ctx.profile.minimum_balance_to_keep}")
    print(f"  GT Safe: {gt['amount_safe_to_pay']}, Pred Safe: {res.amount_safe_to_pay}")
    print(f"  GT Earliest: {gt['earliest_date_for_full_payment']}, Pred Earliest: {res.earliest_date_for_full_payment}")
    print(f"  GT Status: {gt['affordability_status']}, Pred Status: {res.affordability_status}")
    print(f"  GT Method: {gt['recommended_payment_method']}, Pred Method: {res.recommended_payment_method}")
    print(f"  GT Plan: {gt['payment_plan']}")
    print(f"  Pred Plan: {res.payment_plan}")
    print(f"  GT Changes: {gt['spending_changes_needed']}, Pred Changes: {res.spending_changes_needed}\n")
