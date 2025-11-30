#!/usr/bin/env python3
"""
TickerResolver class for resolving company names to ticker symbols.
"""

import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Company:
    """Represents a company with its ticker and name."""
    ticker: str
    title: str
    cik_str: Optional[int] = None
    
    def __str__(self) -> str:
        return f"{self.ticker} - {self.title}"


class TickerResolver:
    """
    Resolves user input (ticker or company name) to a valid ticker symbol.
    
    Usage:
        resolver = TickerResolver()
        ticker = resolver.resolve("Apple")  # Returns "AAPL"
        ticker = resolver.resolve("NVDA")   # Returns "NVDA"
    """
    
    DEFAULT_JSON_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "company_tickers.json"
    )
    
    def __init__(self, json_path: Optional[str] = None):
        """
        Initialize resolver with company data.
        
        Args:
            json_path: Path to company_tickers.json. Uses default if not provided.
        """
        self.json_path = json_path or self.DEFAULT_JSON_PATH
        self._companies: Optional[list[Company]] = None
        self._ticker_map: Optional[dict[str, Company]] = None
    
    @property
    def companies(self) -> list[Company]:
        """Lazy-load company data."""
        if self._companies is None:
            self._load_data()
        return self._companies
    
    @property
    def ticker_map(self) -> dict[str, Company]:
        """Lazy-load ticker lookup map."""
        if self._ticker_map is None:
            self._load_data()
        return self._ticker_map
    
    def _load_data(self):
        """Load company data from JSON file."""
        self._companies = []
        self._ticker_map = {}
        
        try:
            with open(self.json_path, "r") as f:
                data = json.load(f)
            
            for entry in data.values():
                company = Company(
                    ticker=entry.get("ticker", ""),
                    title=entry.get("title", ""),
                    cik_str=entry.get("cik_str")
                )
                self._companies.append(company)
                self._ticker_map[company.ticker.upper()] = company
                
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load company data: {e}")
    
    def resolve(self, user_input: str) -> str:
        """
        Resolve user input to a ticker symbol.
        
        1. First tries exact ticker match (case-insensitive)
        2. Then tries partial company name match (case-insensitive)
        3. Falls back to uppercase input if no match found
        
        Args:
            user_input: Ticker symbol or company name
            
        Returns:
            Resolved ticker symbol
        """
        user_input = user_input.strip()
        input_upper = user_input.upper()
        input_lower = user_input.lower()
        
        # Step 1: Exact ticker match
        if input_upper in self.ticker_map:
            return self.ticker_map[input_upper].ticker
        
        # Step 2: Partial company name match
        for company in self.companies:
            if input_lower in company.title.lower():
                return company.ticker
        
        # No match found - assume valid ticker
        return input_upper
    
    def get_company(self, ticker: str) -> Optional[Company]:
        """
        Get company info by ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Company if found, None otherwise
        """
        return self.ticker_map.get(ticker.upper())
    
    def search(self, query: str, limit: int = 10) -> list[Company]:
        """
        Search companies by name or ticker.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching companies
        """
        query_lower = query.lower()
        results = []
        
        for company in self.companies:
            if (query_lower in company.ticker.lower() or 
                query_lower in company.title.lower()):
                results.append(company)
                if len(results) >= limit:
                    break
        
        return results
    
    def __len__(self) -> int:
        """Return total number of companies."""
        return len(self.companies)
    
    def __iter__(self):
        """Iterate over all companies."""
        return iter(self.companies)

