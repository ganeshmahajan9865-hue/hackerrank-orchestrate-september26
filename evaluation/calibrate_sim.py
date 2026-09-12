import sys, os
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
import datetime

from src.data_loader import load_all_data
from src.data_cleaner import clean_all_data
from src.data_joiner import DataJoiner, RequestContext
from src.image_extractor import ImageExtractor
from src.message_parser import MessageParser
from src.currency_converter import CurrencyConverter
from src.event_reconstructor import EventReconstructor

raw = load_all_data()
clean = clean_all_data(raw)
joiner = DataJoiner(clean)
img_ext = ImageExtractor()
msg_parse = MessageParser()
curr_conv = CurrencyConverter(clean['exchange_rates'])
reconstructor = EventReconstructor(img_ext, msg_parse, curr_conv)
samples = clean['sample_requests']

# First, update event_reconstructor logic to filter recurring categories properly
# Let us inspect how recurring commitments are extracted currently
print("Calibrating forecast engine...")
