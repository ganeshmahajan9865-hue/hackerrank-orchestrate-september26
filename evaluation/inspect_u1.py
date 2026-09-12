import pandas as pd
events = pd.read_csv('dataset/financial_events.csv')
u1 = events[events['user_id'] == 'user_01']
print(u1[['event_id', 'event_date', 'amount', 'category', 'description', 'direction', 'status']].to_string())
