import sys, os
sys.path.insert(0, '.')
import pandas as pd
from src.data_loader import load_all_data

raw = load_all_data()
df = raw['financial_events']
u5 = df[df['user_id'] == 'user_05']

# Check total debits
debits = u5[u5['direction'] == 'debit']
print("Target: 32638.10")
print("Total debits sum:", debits['amount'].sum())
print("Debits count:", len(debits))

# Check 90-day expenses: from Nov 6 to Feb 6
# What would total 90-day expenses be?
# 3 months of rent: 3 * 4972 = 14916
# 3 months of debits: ~12800 * 3 = 38400
# Wait! Look at 32638.10:
# Is 32638.10 roughly 2.5 months of expenses?
print("Monthly debits avg:", debits.groupby(debits['event_date'].str[:7])['amount'].sum().mean())
