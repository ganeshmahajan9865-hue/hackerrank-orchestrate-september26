import sys, os
sys.path.insert(0, '.')
import pandas as pd
from src.data_loader import load_all_data
from src.data_cleaner import clean_all_data
from src.data_joiner import DataJoiner
from src.image_extractor import ImageExtractor
from src.message_parser import MessageParser
from src.currency_converter import CurrencyConverter

raw = load_all_data()
clean = clean_all_data(raw)
joiner = DataJoiner(clean)
img_ext = ImageExtractor()
msg_parse = MessageParser()
curr_conv = CurrencyConverter(clean['exchange_rates'])

# Check request_01 recurring commitments if excluding variable
ctx1 = joiner.get_request_context('request_01')
req_categories = {'rent', 'housing', 'utilities', 'insurance', 'education', 'debt_repayment', 'family_support', 'cloud_storage', 'delivery_membership', 'gym', 'music_subscription', 'streaming'}

past_debits = ctx1.events[(ctx1.events['direction'] == 'debit') & (ctx1.events['event_date'] <= ctx1.request_date) & (ctx1.events['status'] == 'settled')]
recurring_debits = past_debits[past_debits['category'].isin(req_categories) | past_debits['event_type'].isin(['subscription', 'debt_payment'])]

print("Filtered recurring categories for request_01:")
print(recurring_debits.groupby(['category', 'description'])['amount'].agg(['count', 'mean']))
