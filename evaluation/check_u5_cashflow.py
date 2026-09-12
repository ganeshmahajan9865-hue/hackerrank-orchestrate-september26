import sys, os
sys.path.insert(0, '.')
import pandas as pd
from src.data_loader import load_all_data

raw = load_all_data()
df = raw['financial_events']
u5 = df[df['user_id'] == 'user_05']

# Check monthly debits and credits for user_05
debits = u5[u5['direction'] == 'debit']
credits = u5[u5['direction'] == 'credit']

print("Monthly income for user_05:")
print(credits.groupby(credits['event_date'].str[:7])['amount'].sum())

print("\nMonthly debits for user_05:")
print(debits.groupby(debits['event_date'].str[:7])['amount'].sum())
