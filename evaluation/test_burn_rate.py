import sys, os
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
import datetime

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
samples = clean['sample_requests']

print("Evaluating forecast logic across 25 samples...")
for idx, row in samples.iterrows():
    req_id = row['request_id']
    ctx = joiner.get_request_context(req_id)
    recon = reconstructor.reconstruct(ctx)
    
    req_date = datetime.date.fromisoformat(ctx.request_date)
    end_date = req_date + datetime.timedelta(days=90)
    
    comms = recon['recurring_commitments']
    
    evs = ctx.events
    settled_debits = evs[(evs['direction'] == 'debit') & (evs['status'] == 'settled') & (evs['event_date'] <= ctx.request_date)]
    essential_cats = {'groceries', 'transport'}
    prot_val = ctx.profile.expense_categories_to_protect
    if isinstance(prot_val, str) and prot_val:
        prot = set(prot_val.split('|'))
        essential_cats.update(prot.intersection({'dining', 'shopping', 'healthcare', 'entertainment'}))
        
    ess_debits = settled_debits[settled_debits['category'].isin(essential_cats)]
    min_d = pd.to_datetime(settled_debits['event_date'].min())
    max_d = pd.to_datetime(settled_debits['event_date'].max())
    days_hist = max(30, (max_d - min_d).days)
    daily_burn = ess_debits['amount'].sum() / days_hist if len(ess_debits) > 0 else 0.0
    
    if idx < 5:
        print(f"{req_id}: commitments={len(comms)}, daily_burn={daily_burn:,.2f}")
