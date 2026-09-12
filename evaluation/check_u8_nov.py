import sys, os
sys.path.insert(0, '.')
import pandas as pd

df = pd.read_csv('dataset/financial_events.csv')
u8 = df[df['user_id'] == 'user_08']
nov = u8[(u8['event_date'] >= '2024-11-07') & (u8['event_date'] < '2024-11-15') & (u8['direction'] == 'debit')]
print("November 7-15 debits for user_08:")
print(nov[['event_id', 'event_date', 'amount', 'category', 'description']])
print("Sum:", nov['amount'].sum())
