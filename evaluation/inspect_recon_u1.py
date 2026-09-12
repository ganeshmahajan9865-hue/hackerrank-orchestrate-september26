import sys, os
sys.path.insert(0, '.')
from src.data_loader import load_all_data
from src.data_cleaner import clean_all_data
from src.data_joiner import DataJoiner
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

ctx1 = joiner.get_request_context('request_01')
res1 = reconstructor.reconstruct(ctx1)
print(f"Recurring commitments for request_01: {len(res1['recurring_commitments'])}")
for c in res1['recurring_commitments']:
    print(f"  cat={c.category}, desc={c.description}, day={c.day_of_month}, amt={c.amount}")
