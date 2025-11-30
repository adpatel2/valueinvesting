#!/usr/bin/env python3
"""
Database class for storing and querying stock financial data.
"""

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from stock import Stock, ValueFormatter


@dataclass
class StockRecord:
    """Represents a stock record from the database."""
    ticker: str
    company_name: str
    enterprise_value: Optional[float]
    fcf_2025: Optional[float]
    fcf_2024: Optional[float]
    fcf_2023: Optional[float]
    fcf_2022: Optional[float]
    fcf_2021: Optional[float]
    average_fcf: Optional[float]
    fcf_yield: Optional[float]
    last_updated: str
    
    def display(self):
        """Print formatted stock data."""
        fmt = ValueFormatter.format_large_number
        print(f"\n{'='*50}")
        print(f"  {self.ticker} - {self.company_name}")
        print(f"{'='*50}")
        print(f"  Enterprise Value: {fmt(self.enterprise_value)}")
        print(f"  FCF 2025: {fmt(self.fcf_2025)}")
        print(f"  FCF 2024: {fmt(self.fcf_2024)}")
        print(f"  FCF 2023: {fmt(self.fcf_2023)}")
        print(f"  FCF 2022: {fmt(self.fcf_2022)}")
        print(f"  FCF 2021: {fmt(self.fcf_2021)}")
        print(f"  Average FCF: {fmt(self.average_fcf)}")
        print(f"  FCF Yield: {self.fcf_yield if self.fcf_yield is not None else 'N/A'}")
        print(f"  Last Updated: {self.last_updated}")


class StockDatabase:
    """
    SQLite database for storing stock financial data.
    
    Usage:
        db = StockDatabase()
        db.create_tables()
        db.upsert(stock_data, company_name)
        record = db.get("AAPL")
    """
    
    DEFAULT_DB_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        "stocks.db"
    )
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file. Uses default if not provided.
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def create_tables(self):
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_financials (
                    ticker TEXT PRIMARY KEY,
                    company_name TEXT,
                    enterprise_value REAL,
                    fcf_2025 REAL,
                    fcf_2024 REAL,
                    fcf_2023 REAL,
                    fcf_2022 REAL,
                    fcf_2021 REAL,
                    average_fcf REAL,
                    fcf_yield REAL,
                    last_updated TEXT
                )
            """)
            # Add columns if they don't exist (for existing databases)
            for column in ["average_fcf", "fcf_yield"]:
                try:
                    conn.execute(f"ALTER TABLE stock_financials ADD COLUMN {column} REAL")
                except sqlite3.OperationalError:
                    pass  # Column already exists
            conn.commit()
        print(f"Database ready: {self.db_path}")
    
    def _calculate_average_fcf(self, fcf_values: list[Optional[float]]) -> Optional[float]:
        """
        Calculate average FCF with special rules:
        - If any FCF value is negative, return None (N/A)
        - Ignore None values when calculating average
        - Return None if no valid values exist
        """
        valid_values = [v for v in fcf_values if v is not None]
        
        if not valid_values:
            return None
        
        if any(v < 0 for v in valid_values):
            return None
        
        return sum(valid_values) / len(valid_values)
    
    def _calculate_fcf_yield(self, average_fcf: Optional[float], enterprise_value: Optional[float]) -> Optional[float]:
        """
        Calculate FCF yield (average FCF / enterprise value), rounded to 3 decimals.
        
        Returns:
            FCF yield rounded to 3 decimals, or None if:
            - average_fcf is None (N/A)
            - enterprise_value is None, zero, or negative
        """
        if average_fcf is None or enterprise_value is None:
            return None
        if enterprise_value <= 0:
            return None
        return round(average_fcf / enterprise_value, 3)
    
    def upsert(self, data: dict, company_name: str):
        """
        Insert or update stock data.
        Automatically recalculates average_fcf and fcf_yield.
        
        Args:
            data: Dictionary with ticker and financial data
            company_name: Company name
        """
        # Always recalculate average_fcf from the FCF values
        fcf_values = [
            data.get("fcf_2025"),
            data.get("fcf_2024"),
            data.get("fcf_2023"),
            data.get("fcf_2022"),
            data.get("fcf_2021"),
        ]
        average_fcf = self._calculate_average_fcf(fcf_values)
        
        # Always recalculate fcf_yield from average_fcf and enterprise_value
        enterprise_value = data.get("enterprise_value")
        fcf_yield = self._calculate_fcf_yield(average_fcf, enterprise_value)
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO stock_financials 
                (ticker, company_name, enterprise_value, fcf_2025, fcf_2024, 
                 fcf_2023, fcf_2022, fcf_2021, average_fcf, fcf_yield, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["ticker"],
                company_name,
                enterprise_value,
                data.get("fcf_2025"),
                data.get("fcf_2024"),
                data.get("fcf_2023"),
                data.get("fcf_2022"),
                data.get("fcf_2021"),
                average_fcf,
                fcf_yield,
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def get(self, ticker: str) -> Optional[StockRecord]:
        """
        Get stock record by ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            StockRecord if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM stock_financials WHERE ticker = ?", 
                (ticker.upper(),)
            )
            row = cursor.fetchone()
        
        if row:
            return StockRecord(
                ticker=row[0],
                company_name=row[1],
                enterprise_value=row[2],
                fcf_2025=row[3],
                fcf_2024=row[4],
                fcf_2023=row[5],
                fcf_2022=row[6],
                fcf_2021=row[7],
                average_fcf=row[8] if len(row) > 8 else None,
                fcf_yield=row[9] if len(row) > 9 else None,
                last_updated=row[10] if len(row) > 10 else row[8]
            )
        return None
    
    def get_all(self) -> list[StockRecord]:
        """Get all stock records."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM stock_financials ORDER BY ticker")
            rows = cursor.fetchall()
        
        return [
            StockRecord(
                ticker=row[0],
                company_name=row[1],
                enterprise_value=row[2],
                fcf_2025=row[3],
                fcf_2024=row[4],
                fcf_2023=row[5],
                fcf_2022=row[6],
                fcf_2021=row[7],
                average_fcf=row[8] if len(row) > 8 else None,
                fcf_yield=row[9] if len(row) > 9 else None,
                last_updated=row[10] if len(row) > 10 else row[8]
            )
            for row in rows
        ]
    
    def count(self) -> int:
        """Get total number of records."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM stock_financials")
            return cursor.fetchone()[0]
    
    def get_top_by_yield(self, limit: int = 30) -> list[StockRecord]:
        """Get top stocks sorted by FCF yield (highest first)."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM stock_financials 
                WHERE fcf_yield IS NOT NULL 
                ORDER BY fcf_yield DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
        
        return [
            StockRecord(
                ticker=row[0],
                company_name=row[1],
                enterprise_value=row[2],
                fcf_2025=row[3],
                fcf_2024=row[4],
                fcf_2023=row[5],
                fcf_2022=row[6],
                fcf_2021=row[7],
                average_fcf=row[8] if len(row) > 8 else None,
                fcf_yield=row[9] if len(row) > 9 else None,
                last_updated=row[10] if len(row) > 10 else row[8]
            )
            for row in rows
        ]
    
    def update_fcf(self, ticker: str, year: int, value: Optional[float]) -> bool:
        """
        Update a single FCF year value and automatically recalculate average_fcf and fcf_yield.
        
        Args:
            ticker: Stock ticker symbol
            year: Year to update (2021-2025)
            value: New FCF value (or None to clear)
            
        Returns:
            True if updated, False if ticker not found
        """
        if year not in (2021, 2022, 2023, 2024, 2025):
            raise ValueError(f"Year must be 2021-2025, got {year}")
        
        # Get existing record
        record = self.get(ticker)
        if record is None:
            return False
        
        # Build current FCF values, updating the specified year
        fcf_values = {
            2025: record.fcf_2025,
            2024: record.fcf_2024,
            2023: record.fcf_2023,
            2022: record.fcf_2022,
            2021: record.fcf_2021,
        }
        fcf_values[year] = value
        
        # Recalculate average and yield
        average_fcf = self._calculate_average_fcf(list(fcf_values.values()))
        fcf_yield = self._calculate_fcf_yield(average_fcf, record.enterprise_value)
        
        # Update the database
        with self._get_connection() as conn:
            conn.execute(f"""
                UPDATE stock_financials 
                SET fcf_{year} = ?, average_fcf = ?, fcf_yield = ?, last_updated = ?
                WHERE ticker = ?
            """, (value, average_fcf, fcf_yield, datetime.now().isoformat(), ticker.upper()))
            conn.commit()
        
        return True
    
    def update_enterprise_value(self, ticker: str, value: Optional[float]) -> bool:
        """
        Update enterprise value and automatically recalculate fcf_yield.
        
        Args:
            ticker: Stock ticker symbol
            value: New enterprise value (or None to clear)
            
        Returns:
            True if updated, False if ticker not found
        """
        # Get existing record
        record = self.get(ticker)
        if record is None:
            return False
        
        # Recalculate yield with new enterprise value
        fcf_yield = self._calculate_fcf_yield(record.average_fcf, value)
        
        # Update the database
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE stock_financials 
                SET enterprise_value = ?, fcf_yield = ?, last_updated = ?
                WHERE ticker = ?
            """, (value, fcf_yield, datetime.now().isoformat(), ticker.upper()))
            conn.commit()
        
        return True
    
    def delete(self, ticker: str) -> bool:
        """
        Delete a stock record.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM stock_financials WHERE ticker = ?",
                (ticker.upper(),)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def clear(self):
        """Delete all records from the database."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM stock_financials")
            conn.commit()

