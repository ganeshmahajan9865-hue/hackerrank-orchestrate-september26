import sys, os
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
import datetime
from src.data_loader import load_all_data
from src.data_cleaner import clean_all_data
from src.data_joiner import DataJoiner

raw = load_all_data()
clean = clean_all_data(raw)
joiner = DataJoiner(clean)
samples = clean['sample_requests']

print("Checking fixed commitment logic across all 25 sample requests...")
