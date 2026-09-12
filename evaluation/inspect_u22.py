import sys, os
sys.path.insert(0, '.')
import pandas as pd
from src.data_loader import load_all_data
raw = load_all_data()
df = raw['financial_events']
u22 = df[df['user_id'] == 'user_22']
print("User 22 debits around request date (2024-12-05):")
print(u22[(u22['event_date'] >= '2024-11-01') & (u22['direction'] == 'debit')][['event_id', 'event_date', 'amount', 'category', 'description', 'status', 'flexibility']])
