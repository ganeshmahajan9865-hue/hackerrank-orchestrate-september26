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

raw = load_all_data()
clean = clean_all_data(raw)
joiner = DataJoiner(clean)
img_ext = ImageExtractor()
msg_parse = MessageParser()
curr_conv = CurrencyConverter(clean['exchange_rates'])
reconstructor = EventReconstructor(img_ext, msg_parse, curr_conv)
forecast = ForecastEngine()
samples = clean['sample_requests']

print(f"{'Req ID':<10} {'GT Safe':>14} {'Pred Safe':>14} {'Diff':>14} {'Ratio':>10}")
for _, row in samples.iterrows():
    ctx = joiner.get_request_context(row['request_id'])
    recon = reconstructor.reconstruct(ctx)
    pred_safe = forecast.calculate_amount_safe_to_pay(ctx, recon)
    gt_safe = row['amount_safe_to_pay']
    diff = pred_safe - gt_safe
    ratio = pred_safe / gt_safe if gt_safe > 0 else 0
    print(f"{row['request_id']:<10} {gt_safe:>14,.2f} {pred_safe:>14,.2f} {diff:>14,.2f} {ratio:>10.2f}")
