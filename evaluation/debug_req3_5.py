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

for req_id in ['request_03', 'request_05']:
    ctx = joiner.get_request_context(req_id)
    recon = reconstructor.reconstruct(ctx)
    sim = forecast.simulate(ctx, recon)
    print(f"=== {req_id} Baseline Sim ===")
    print(f"  Curr Bal: {ctx.profile.current_available_balance}, Min Bal: {ctx.profile.minimum_balance_to_keep}")
    print(f"  Min Bal Seen: {sim.min_balance_observed}, Min Headroom: {sim.min_headroom}")
    print(f"  Is Safe: {sim.is_safe}, Breach Date: {sim.breach_date}")
