"""
Currency Converter Module

Converts transaction and request amounts to the target currency using fixed dated
exchange rates from exchange_rates.csv. Never estimates or invents rates.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import Dict, Tuple, Optional
import pandas as pd


class CurrencyConverter:
    """Fast indexed exchange rate converter using dated FX rates."""

    def __init__(self, exchange_rates_df: pd.DataFrame):
        self.rates_df = exchange_rates_df.copy()
        # Sort by rate_date ascending
        self.rates_df['rate_date'] = pd.to_datetime(self.rates_df['rate_date'])
        self.rates_df = self.rates_df.sort_values('rate_date')
        
        # Build lookup: (from, to) -> list of (date, rate)
        self.rate_map: Dict[Tuple[str, str], list] = {}
        for _, row in self.rates_df.iterrows():
            pair = (row['from_currency'], row['to_currency'])
            self.rate_map.setdefault(pair, []).append((row['rate_date'], float(row['rate'])))

    def get_rate(self, from_curr: str, to_curr: str, date_str: str) -> float:
        """Retrieves exact or closest preceding exchange rate for the dated currency pair."""
        from_curr = from_curr.upper()
        to_curr = to_curr.upper()
        if from_curr == to_curr:
            return 1.0

        target_date = pd.to_datetime(date_str)
        
        # Direct lookup
        if (from_curr, to_curr) in self.rate_map:
            quotes = self.rate_map[(from_curr, to_curr)]
            # Find closest quote on or before target_date
            valid_quotes = [q for q in quotes if q[0] <= target_date]
            if valid_quotes:
                return valid_quotes[-1][1]
            return quotes[0][1]

        # Inverse lookup
        if (to_curr, from_curr) in self.rate_map:
            quotes = self.rate_map[(to_curr, from_curr)]
            valid_quotes = [q for q in quotes if q[0] <= target_date]
            if valid_quotes:
                return 1.0 / valid_quotes[-1][1]
            return 1.0 / quotes[0][1]

        raise ValueError(f"No exchange rate found between {from_curr} and {to_curr} for date {date_str}")

    def convert(self, amount: float, from_curr: str, to_curr: str, date_str: str) -> float:
        """Converts amount from from_curr to to_curr on date_str."""
        if from_curr.upper() == to_curr.upper():
            return float(amount)
        rate = self.get_rate(from_curr, to_curr, date_str)
        return float(amount * rate)


if __name__ == '__main__':
    from src.data_loader import load_all_data
    from src.data_cleaner import clean_all_data

    print('Testing currency_converter.py...')
    raw = load_all_data()
    clean = clean_all_data(raw)
    converter = CurrencyConverter(clean['exchange_rates'])
    
    # Test USD to IDR on 2023-10-15
    rate = converter.get_rate('USD', 'IDR', '2023-10-15')
    print(f"USD to IDR on 2023-10-15: {rate}")
    assert rate == 15833.33, f"Expected 15833.33, got {rate}"
    
    # Test conversion of USD 100 to IDR
    idr = converter.convert(100.0, 'USD', 'IDR', '2023-10-15')
    print(f"USD 100.0 -> IDR {idr:,.2f}")
    assert round(idr, 2) == 1583333.0, f"Expected 1583333.0, got {idr}"
    
    # Test same currency
    same = converter.convert(500.0, 'EUR', 'EUR', '2024-01-01')
    assert same == 500.0, "Same currency conversion must be identity"
    
    print('Currency conversion test passed successfully!')
