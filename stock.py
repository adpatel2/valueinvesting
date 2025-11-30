#!/usr/bin/env python3
"""
Stock class for fetching financial data from Yahoo Finance.
"""

from dataclasses import dataclass
from typing import Optional

import yfinance as yf


@dataclass
class FreeCashFlowData:
    """Container for annual free cash flow data."""
    fcf_2025: Optional[float] = None
    fcf_2024: Optional[float] = None
    fcf_2023: Optional[float] = None
    fcf_2022: Optional[float] = None
    fcf_2021: Optional[float] = None
    
    def to_dict(self) -> dict[str, Optional[float]]:
        return {
            "2025": self.fcf_2025,
            "2024": self.fcf_2024,
            "2023": self.fcf_2023,
            "2022": self.fcf_2022,
            "2021": self.fcf_2021,
        }
    
    def __iter__(self):
        """Iterate over years and values."""
        for year, value in self.to_dict().items():
            yield year, value
    
    def calculate_average(self) -> Optional[float]:
        """
        Calculate average FCF with special rules:
        - If any FCF value is negative, return None (N/A)
        - Ignore N/A (None) values when calculating average
        - Return None if no valid values exist
        
        Returns:
            Average FCF or None if any value is negative or no data
        """
        values = [self.fcf_2025, self.fcf_2024, self.fcf_2023, self.fcf_2022, self.fcf_2021]
        
        # Filter out None values
        valid_values = [v for v in values if v is not None]
        
        # If no valid values, return None
        if not valid_values:
            return None
        
        # If any value is negative, return None
        if any(v < 0 for v in valid_values):
            return None
        
        # Calculate average of positive values
        return sum(valid_values) / len(valid_values)


class Stock:
    """
    Represents a stock and provides methods to fetch financial data.
    
    Usage:
        stock = Stock("AAPL")
        ev = stock.get_enterprise_value()
        fcf = stock.get_free_cash_flow()
    """
    
    TARGET_YEARS = [2025, 2024, 2023, 2022, 2021]
    
    def __init__(self, ticker: str):
        """
        Initialize Stock with a ticker symbol.
        
        Args:
            ticker: Stock ticker symbol (e.g., "AAPL", "NVDA")
        """
        self.ticker = ticker.upper().strip()
        self._yf_ticker: Optional[yf.Ticker] = None
        self._info: Optional[dict] = None
        self._cash_flow = None
        self._quarterly_cash_flow = None
    
    @property
    def yf_ticker(self) -> yf.Ticker:
        """Lazy-load yfinance Ticker object."""
        if self._yf_ticker is None:
            self._yf_ticker = yf.Ticker(self.ticker)
        return self._yf_ticker
    
    @property
    def info(self) -> dict:
        """Lazy-load stock info."""
        if self._info is None:
            self._info = self.yf_ticker.info
        return self._info
    
    @property
    def cash_flow(self):
        """Lazy-load annual cash flow statement."""
        if self._cash_flow is None:
            self._cash_flow = self.yf_ticker.cash_flow
        return self._cash_flow
    
    @property
    def quarterly_cash_flow(self):
        """Lazy-load quarterly cash flow statement."""
        if self._quarterly_cash_flow is None:
            self._quarterly_cash_flow = self.yf_ticker.quarterly_cash_flow
        return self._quarterly_cash_flow
    
    def get_enterprise_value(self) -> Optional[float]:
        """
        Fetch enterprise value from Yahoo Finance.
        
        Returns:
            Enterprise value as float, or None if not available.
        """
        try:
            return self.info.get("enterpriseValue")
        except Exception:
            return None
    
    def _calculate_ttm_fcf(self) -> Optional[float]:
        """Calculate TTM Free Cash Flow from quarterly data (sum of last 4 quarters)."""
        try:
            if self.quarterly_cash_flow.empty:
                return None
            if "Free Cash Flow" not in self.quarterly_cash_flow.index:
                return None
            
            fcf_row = self.quarterly_cash_flow.loc["Free Cash Flow"]
            valid_quarters = []
            
            for col in self.quarterly_cash_flow.columns[:4]:
                val = fcf_row[col]
                if val is not None and not (isinstance(val, float) and val != val):
                    valid_quarters.append(val)
            
            if len(valid_quarters) == 4:
                return sum(valid_quarters)
            return None
        except Exception:
            return None
    
    def get_free_cash_flow(self) -> FreeCashFlowData:
        """
        Fetch annual free cash flow data.
        If 2025 data is not available, uses TTM (sum of last 4 quarters).
        
        Returns:
            FreeCashFlowData object with FCF for each year.
        """
        result = FreeCashFlowData()
        
        try:
            # Get annual FCF
            if not self.cash_flow.empty and "Free Cash Flow" in self.cash_flow.index:
                fcf_row = self.cash_flow.loc["Free Cash Flow"]
                
                for col in self.cash_flow.columns:
                    year = col.year
                    if year in self.TARGET_YEARS:
                        value = fcf_row[col]
                        if value is not None and not (isinstance(value, float) and value != value):
                            setattr(result, f"fcf_{year}", value)
            
            # If 2025 is not available, use TTM
            if result.fcf_2025 is None:
                ttm_fcf = self._calculate_ttm_fcf()
                if ttm_fcf is not None:
                    result.fcf_2025 = ttm_fcf
            
        except Exception:
            pass
        
        return result
    
    def get_all_data(self) -> dict:
        """
        Fetch all financial data (enterprise value + FCF + average FCF).
        
        Returns:
            Dictionary with all financial data.
        """
        fcf = self.get_free_cash_flow()
        return {
            "ticker": self.ticker,
            "enterprise_value": self.get_enterprise_value(),
            "fcf_2025": fcf.fcf_2025,
            "fcf_2024": fcf.fcf_2024,
            "fcf_2023": fcf.fcf_2023,
            "fcf_2022": fcf.fcf_2022,
            "fcf_2021": fcf.fcf_2021,
            "average_fcf": fcf.calculate_average(),
        }
    
    def __repr__(self) -> str:
        return f"Stock('{self.ticker}')"
    
    def __str__(self) -> str:
        return self.ticker


class ValueFormatter:
    """Utility class for formatting financial values."""
    
    @staticmethod
    def format_large_number(value: Optional[float], include_sign: bool = True) -> str:
        """
        Format large numbers with B/M/T suffixes.
        
        Args:
            value: The value to format
            include_sign: Whether to include negative sign for negative values
            
        Returns:
            Formatted string (e.g., "$1.23B") or "N/A" if value is None
        """
        if value is None:
            return "N/A"
        
        negative = value < 0
        abs_value = abs(value)
        
        if abs_value >= 1_000_000_000_000:
            formatted = f"${abs_value / 1_000_000_000_000:.2f}T"
        elif abs_value >= 1_000_000_000:
            formatted = f"${abs_value / 1_000_000_000:.2f}B"
        elif abs_value >= 1_000_000:
            formatted = f"${abs_value / 1_000_000:.2f}M"
        else:
            formatted = f"${abs_value:,.2f}"
        
        if negative and include_sign:
            return f"-{formatted}"
        return formatted

