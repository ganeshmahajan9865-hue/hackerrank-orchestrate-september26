import sys, os
sys.path.insert(0, '.')
import pandas as pd
import datetime

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

ctx18 = joiner.get_request_context('request_18')
recon18 = reconstructor.reconstruct(ctx18)

# Check simulation on 2026-08-15 vs 2026-09-15
req_amt = ctx18.requested_amount
sim_aug = forecast.simulate(ctx18, recon18, [('2026-08-15', req_amt)])
sim_sep = forecast.simulate(ctx18, recon18, [('2026-09-15', req_amt)])

print(f"August 15 safe: {sim_aug.is_safe}, min_balance: {sim_aug.min_balance_observed}, min_headroom: {sim_aug.min_headroom}, breach: {sim_aug.breach_date}")
print(f"Sept 15 safe: {sim_sep.is_safe}, min_balance: {sim_sep.min_balance_observed}, min_headroom: {sim_sep.min_headroom}, breach: {sim_sep.breach_date}")
