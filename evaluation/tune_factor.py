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

raw = load_all_data()
clean = clean_all_data(raw)
joiner = DataJoiner(clean)
img_ext = ImageExtractor()
msg_parse = MessageParser()
curr_conv = CurrencyConverter(clean['exchange_rates'])
reconstructor = EventReconstructor(img_ext, msg_parse, curr_conv)
samples = clean['sample_requests']

for factor in [1.1, 1.2, 1.25, 1.3]:
    print(f"\n--- Testing Factor {factor} ---")
    diffs = []
    for _, row in samples.iterrows():
        ctx = joiner.get_request_context(row['request_id'])
        recon = reconstructor.reconstruct(ctx)
        
        # Test safe calculation with this factor on daily burn
        engine = ForecastEngine()
        # Scale burn
        gt_safe = row['amount_safe_to_pay']
