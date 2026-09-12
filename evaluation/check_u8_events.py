import sys, os
sys.path.insert(0, '.')
import pandas as pd

df = pd.read_csv('dataset/financial_events.csv')
u8 = df[df['user_id'] == 'user_08']
print(u8[u8['amount'].isin([89.0, 177.0, 80.9, 76.07, 29.03])][['event_id', 'event_date', 'amount', 'category', 'description']])
