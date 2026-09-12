import pandas as pd
events = pd.read_csv('dataset/financial_events.csv')
target_ids = ['event_476', 'event_989', 'event_1815', 'event_1816']
print(events[events['event_id'].isin(target_ids)][['event_id', 'user_id', 'event_date', 'amount', 'category', 'description', 'flexibility', 'minimum_allowed_amount']])
