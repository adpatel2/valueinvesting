#!/usr/bin/env python3
"""
Ingestion script to populate SQLite database with stock financial data.
Uses Stock and StockDatabase classes for clean OOP design.
"""

import argparse
import time

from database import StockDatabase
from stock import Stock, ValueFormatter
from ticker_resolver import TickerResolver


class StockIngestion:
    """
    Handles bulk ingestion of stock data into the database.
    
    Usage:
        ingestion = StockIngestion()
        ingestion.run(limit=10)  # Ingest first 10 tickers
        ingestion.run()          # Ingest all tickers
    """
    
    def __init__(self, delay: float = 0.5):
        """
        Initialize ingestion with dependencies.
        
        Args:
            delay: Delay between API calls in seconds (rate limiting)
        """
        self.delay = delay
        self.resolver = TickerResolver()
        self.db = StockDatabase()
    
    def ingest_single(self, ticker: str, company_name: str) -> bool:
        """
        Ingest a single stock into the database.
        
        Args:
            ticker: Stock ticker symbol
            company_name: Company name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            stock = Stock(ticker)
            data = stock.get_all_data()
            self.db.upsert(data, company_name)
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def run(self, limit: int | None = None):
        """
        Run ingestion for all tickers.
        
        Args:
            limit: Optional limit on number of tickers to process
        """
        # Ensure database exists
        self.db.create_tables()
        
        # Get companies to process
        companies = list(self.resolver.companies)
        if limit:
            companies = companies[:limit]
        
        total = len(companies)
        print(f"\nStarting ingestion of {total} tickers...")
        print("=" * 70)
        
        success_count = 0
        error_count = 0
        fmt = ValueFormatter.format_large_number
        
        for i, company in enumerate(companies, 1):
            ticker = company.ticker
            name = company.title
            
            print(f"[{i}/{total}] Processing {ticker} ({name})...", end=" ")
            
            try:
                stock = Stock(ticker)
                data = stock.get_all_data()
                self.db.upsert(data, name)
                
                ev = fmt(data["enterprise_value"])
                fcf = fmt(data["fcf_2025"])
                print(f"✓ EV: {ev}, FCF 2025: {fcf}")
                success_count += 1
                
            except Exception as e:
                print(f"✗ Error: {e}")
                error_count += 1
            
            # Rate limiting
            if i < total:
                time.sleep(self.delay)
        
        print("=" * 70)
        print(f"\nIngestion complete!")
        print(f"  Success: {success_count}")
        print(f"  Errors: {error_count}")
        print(f"  Database: {self.db.db_path}")


def interactive_mode():
    """Run interactive menu."""
    print("=" * 50)
    print("  Stock Financial Data Ingestion")
    print("=" * 50)
    print("\nOptions:")
    print("  1. Ingest all tickers (full)")
    print("  2. Ingest limited tickers (test)")
    print("  3. Show database stats")
    print("  4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        confirm = input("This will process ALL tickers. Continue? (y/n): ").strip().lower()
        if confirm == "y":
            ingestion = StockIngestion()
            ingestion.run()
    elif choice == "2":
        limit = input("Enter number of tickers to process: ").strip()
        try:
            ingestion = StockIngestion()
            ingestion.run(limit=int(limit))
        except ValueError:
            print("Invalid number.")
    elif choice == "3":
        db = StockDatabase()
        count = db.count()
        print(f"\nDatabase contains {count} stock records.")
        print(f"Location: {db.db_path}")
    elif choice == "4":
        print("Exiting.")
    else:
        print("Invalid choice.")


def ingest_single_ticker(ticker: str):
    """Ingest or re-ingest a single ticker."""
    ingestion = StockIngestion()
    ingestion.db.create_tables()
    
    # Resolve ticker to get company name
    company = ingestion.resolver.get_company(ticker)
    if company:
        name = company.title
    else:
        name = ticker.upper()
    
    print(f"\nIngesting {ticker.upper()} ({name})...", end=" ")
    
    try:
        stock = Stock(ticker)
        data = stock.get_all_data()
        ingestion.db.upsert(data, name)
        
        fmt = ValueFormatter.format_large_number
        print(f"✓")
        print(f"  Enterprise Value: {fmt(data['enterprise_value'])}")
        print(f"  FCF 2025: {fmt(data['fcf_2025'])}")
        print(f"  Average FCF: {fmt(data['average_fcf'])}")
    except Exception as e:
        print(f"✗ Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Stock Financial Data Ingestion")
    parser.add_argument("--ticker", type=str, help="Ingest a single ticker")
    parser.add_argument("--limit", type=int, help="Limit number of tickers to process")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between API calls (seconds)")
    parser.add_argument("--interactive", action="store_true", help="Run interactive menu")
    
    args = parser.parse_args()
    
    if args.ticker:
        ingest_single_ticker(args.ticker)
    elif args.interactive:
        interactive_mode()
    else:
        # Default: run ingestion
        ingestion = StockIngestion(delay=args.delay)
        ingestion.run(limit=args.limit)


if __name__ == "__main__":
    main()
