import sys, os
sys.path.insert(0, '.')
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
forecast = ForecastEngine(conservative_buffer=1.0)
plan_engine = PaymentPlanEngine()
decision_engine = DecisionEngine(forecast, plan_engine)
samples = clean['sample_requests']

correct = 0
for _, row in samples.iterrows():
    ctx = joiner.get_request_context(row['request_id'])
    recon = reconstructor.reconstruct(ctx)
    res = decision_engine.evaluate(ctx, recon)
    match = (res.affordability_status == row['affordability_status']) and (res.recommended_payment_method == row['recommended_payment_method'])
    if match: correct += 1
    flag = "OK" if match else "DIFF"
    print(f"{row['request_id']}: Pred={res.affordability_status}/{res.recommended_payment_method} | GT={row['affordability_status']}/{row['recommended_payment_method']} | {flag}")

print(f"\nTotal match: {correct}/25 ({correct/25*100:.1f}%)")
