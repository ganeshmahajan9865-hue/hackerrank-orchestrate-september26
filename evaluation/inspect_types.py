import pandas as pd
events = pd.read_csv('dataset/financial_events.csv')
print("Unique event_type:")
print(events['event_type'].value_counts(dropna=False))
print("\nUnique category:")
print(events['category'].value_counts(dropna=False))
print("\nCategory vs event_type:")
print(pd.crosstab(events['category'], events['event_type']))
