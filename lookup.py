#!/usr/bin/env python3
"""
CLI script to lookup stock financial data from the database.
"""

import argparse

from database import StockDatabase
from ticker_resolver import TickerResolver


def lookup(ticker: str):
    """
    Lookup and display financial data for a stock from the database.
    
    Args:
        ticker: Stock ticker symbol
    """
    db = StockDatabase()
    record = db.get(ticker)
    
    if record:
        record.display()
    else:
        print(f"\nTicker '{ticker}' not found in database.")
        print("Run 'python ingestion_all.py' to populate the database.")


def main():
    parser = argparse.ArgumentParser(
        description="Lookup stock financial data from database",
        usage="python lookup.py TICKER"
    )
    parser.add_argument(
        "ticker", 
        nargs="?",
        help="Stock ticker or company name (e.g., NVDA, Apple)"
    )
    
    args = parser.parse_args()
    
    # Interactive mode if no ticker provided
    if not args.ticker:
        print("=" * 50)
        print("  Stock Financial Data Lookup")
        print("=" * 50)
        user_input = input("\nEnter ticker or company name: ").strip()
        if not user_input:
            print("No input entered. Exiting.")
            return
    else:
        user_input = args.ticker
    
    # Resolve input to ticker
    resolver = TickerResolver()
    ticker = resolver.resolve(user_input)
    
    if ticker != user_input.upper():
        print(f"Resolved '{user_input}' → {ticker}")
    
    lookup(ticker)


if __name__ == "__main__":
    main()

