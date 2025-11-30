#!/usr/bin/env python3
"""
Flask web app to display top stocks ranked by FCF yield.
Includes scheduled jobs to refresh EV daily and FCF every 2 months.
"""

from datetime import datetime
from flask import Flask, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler
from database import StockDatabase
from stock import Stock, ValueFormatter

app = Flask(__name__)


def refresh_enterprise_values():
    """Fetch latest enterprise values from Yahoo Finance and update database."""
    print(f"\n[{datetime.now()}] Starting daily EV refresh...")
    db = StockDatabase()
    records = db.get_all()
    
    success = 0
    errors = 0
    
    for record in records:
        try:
            stock = Stock(record.ticker)
            new_ev = stock.get_enterprise_value()
            if new_ev is not None:
                db.update_enterprise_value(record.ticker, new_ev)
                success += 1
        except Exception as e:
            print(f"  Error updating {record.ticker}: {e}")
            errors += 1
    
    print(f"[{datetime.now()}] EV refresh complete: {success} updated, {errors} errors")


def refresh_fcf_values():
    """Fetch latest FCF values from Yahoo Finance and update database."""
    print(f"\n[{datetime.now()}] Starting bi-monthly FCF refresh...")
    db = StockDatabase()
    records = db.get_all()
    
    success = 0
    errors = 0
    
    for record in records:
        try:
            stock = Stock(record.ticker)
            fcf_data = stock.get_free_cash_flow()
            
            for year in [2025, 2024, 2023, 2022, 2021]:
                fcf_value = getattr(fcf_data, f"fcf_{year}")
                if fcf_value is not None:
                    db.update_fcf(record.ticker, year, fcf_value)
            
            success += 1
        except Exception as e:
            print(f"  Error updating FCF for {record.ticker}: {e}")
            errors += 1
    
    print(f"[{datetime.now()}] FCF refresh complete: {success} updated, {errors} errors")


# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(refresh_enterprise_values, 'cron', hour=22, minute=0)  # 10 PM daily
scheduler.add_job(refresh_fcf_values, 'cron', month='1,3,5,7,9,11', day=1, hour=22, minute=30)  # Every 2 months
scheduler.start()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Top 30 Stocks by FCF Yield</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a24;
            --accent: #00d4aa;
            --accent-dim: #00d4aa33;
            --text-primary: #e8e8ed;
            --text-secondary: #8888a0;
            --border: #2a2a3a;
            --rank-gold: #ffd700;
            --rank-silver: #c0c0c0;
            --rank-bronze: #cd7f32;
        }
        
        body {
            font-family: 'Space Grotesk', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 40px 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            margin-bottom: 50px;
        }
        
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent), #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: var(--text-secondary);
            font-size: 1.1rem;
        }
        
        .stats {
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-top: 20px;
        }
        
        .stat {
            text-align: center;
        }
        
        .stat-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.8rem;
            font-weight: 600;
            color: var(--accent);
        }
        
        .stat-label {
            font-size: 0.85rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            background: var(--bg-secondary);
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
        }
        
        th {
            background: var(--bg-card);
            padding: 18px 16px;
            text-align: left;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-secondary);
            border-bottom: 2px solid var(--border);
        }
        
        th:first-child {
            text-align: center;
            width: 70px;
        }
        
        td {
            padding: 16px;
            border-bottom: 1px solid var(--border);
        }
        
        tr:last-child td {
            border-bottom: none;
        }
        
        tr:hover {
            background: var(--bg-card);
        }
        
        .rank {
            text-align: center;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            font-size: 1.1rem;
        }
        
        .rank-1 { color: var(--rank-gold); }
        .rank-2 { color: var(--rank-silver); }
        .rank-3 { color: var(--rank-bronze); }
        
        .ticker {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            color: var(--accent);
            font-size: 1rem;
        }
        
        .company {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 2px;
        }
        
        .yield {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--accent);
        }
        
        .money {
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-primary);
        }
        
        .text-right {
            text-align: right;
        }
        
        @media (max-width: 768px) {
            h1 { font-size: 1.8rem; }
            .stats { flex-direction: column; gap: 15px; }
            th, td { padding: 12px 10px; font-size: 0.85rem; }
            .yield { font-size: 1rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Top 30 Stocks by FCF Yield</h1>
            <p class="subtitle">Ranked by Free Cash Flow Yield (Average FCF / Enterprise Value)</p>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{{ total_stocks }}</div>
                    <div class="stat-label">Total Stocks</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ stocks|length }}</div>
                    <div class="stat-label">Showing</div>
                </div>
            </div>
            <p class="subtitle" style="margin-top: 20px; font-size: 0.9rem;">
                Last refreshed: {{ last_refreshed }}
            </p>
        </header>
        
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Stock</th>
                    <th class="text-right">FCF Yield</th>
                    <th class="text-right">Avg FCF</th>
                    <th class="text-right">Enterprise Value</th>
                </tr>
            </thead>
            <tbody>
                {% for stock in stocks %}
                <tr>
                    <td class="rank rank-{{ loop.index }}">{{ loop.index }}</td>
                    <td>
                        <div class="ticker">{{ stock.ticker }}</div>
                        <div class="company">{{ stock.company_name }}</div>
                    </td>
                    <td class="text-right yield">{{ "%.3f"|format(stock.fcf_yield) }}</td>
                    <td class="text-right money">{{ format_number(stock.average_fcf) }}</td>
                    <td class="text-right money">{{ format_number(stock.enterprise_value) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    db = StockDatabase()
    stocks = db.get_top_by_yield(limit=30)
    total_stocks = db.count()
    last_refreshed = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return render_template_string(
        HTML_TEMPLATE,
        stocks=stocks,
        total_stocks=total_stocks,
        last_refreshed=last_refreshed,
        format_number=ValueFormatter.format_large_number
    )


if __name__ == "__main__":
    print("Starting server at http://localhost:8080")
    app.run(debug=True, port=8080)

