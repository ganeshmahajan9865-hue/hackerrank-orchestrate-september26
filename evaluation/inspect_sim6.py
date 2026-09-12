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

ctx6 = joiner.get_request_context('request_06')
recon6 = reconstructor.reconstruct(ctx6)
print("Commitments for request_06:")
for c in recon6['recurring_commitments']:
    print(f"  {c.category}: {c.description}, day={c.day_of_month}, amt={c.amount}, last={c.last_event_date}")

sim6 = forecast.simulate(ctx6, recon6)
print("Sim6 min headroom:", sim6.min_headroom)
print("Sim6 is safe:", sim6.is_safe)
