import sys, os
sys.path.insert(0, '.')
import pandas as pd

df = pd.read_csv('dataset/financial_events.csv')
u8 = df[df['user_id'] == 'user_08']
dec = u8[(u8['event_date'] >= '2024-12-07') & (u8['event_date'] < '2024-12-15') & (u8['direction'] == 'debit')]
print("December 7-15 debits for user_08:")
print(dec[['event_id', 'event_date', 'amount', 'category', 'description']])
print("Sum:", dec['amount'].sum())
