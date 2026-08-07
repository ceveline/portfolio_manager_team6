# Portfolio Manager

A stock portfolio management app that tracks holdings, transactions, and portfolio value in real-time.

## Team Members

1. Kelly Morilla
2. David Soriano
3. Ceveline Evangelista

## Features

- **Buy & Sell Stocks** — Add and remove multiple stocks from your portfolio
- **Auto Price Lookup** — Ticker dropdown with auto-populated current prices from Yahoo Finance
- **Portfolio Summary** — Live total portfolio value and share count in header
- **Holdings Table** — See total shares, average cost, market value, and P&L per ticker
- **Transaction History** — Complete record of all buys and sells with advanced filtering
- **Performance Chart** — Line chart showing portfolio value over time
- **Win Rate Tracking** — Percentage of profitable sell transactions

## Stack

- Python / Flask
- Flask-SQLAlchemy (MySQL with PyMySQL)
- Plain HTML/JS frontend (no framework)
- Swagger docs via flasgger
- yfinance + curl_cffi (stock price data with TLS fingerprinting)
- Chart.js (performance and P&L charting)

## Setup & Running

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Database Setup

#### Prerequisites

- MySQL server running (macOS: `brew services start mysql`)
- Root user access to MySQL

#### Create Database and Tables

```bash
# Create database
mysql -u root -e "CREATE DATABASE IF NOT EXISTS portfolio_manager;"

# Create tables (using Flask-SQLAlchemy)
python -c "from app import create_app, db; app = create_app(); with app.app_context(): db.create_all()"
```

#### Load Sample Data (Optional)

To populate the database with sample transactions, holdings, and price history:

```bash
# Run all three data migrations in order
mysql -u root portfolio_manager < data_migrations/001_add_transactions.sql
mysql -u root portfolio_manager < data_migrations/002_add_holdings.sql
mysql -u root portfolio_manager < data_migrations/003_add_price_history.sql
```

Or run individually if needed. See `data_migrations/README.md` for details.

### 4. Configuration

Create a `.env` file in the project root:

```env
DATABASE_URL=mysql+pymysql://root@127.0.0.1:3306/portfolio_manager
```

Alternatively, use individual MySQL env vars:

```env
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DB=portfolio_manager
```

### 5. Run the Application

```bash
python run.py
```

The app starts in debug mode on `http://localhost:5001`

- **Frontend:** http://localhost:5001 (HTML/JS UI)
- **API:** http://localhost:5001/api/* (REST endpoints)
- **Swagger UI:** http://localhost:5001/apidocs (interactive API docs)

## Database Schema

### Tables

- **users** — User account information
- **holdings** — Current stock positions (ticker, quantity, purchase price, date)
- **transactions** — Complete audit trail of all buy/sell actions
- **price_history** — Daily closing prices for historical analysis

### Key Relationships

- Transactions are the source of truth
- Holdings are calculated from transaction history (net buys - sells)
- Price history is used for portfolio value calculations and performance charting

## API Endpoints

### Holdings & Transactions

- `GET /api/holdings` — List all current holdings (ticker, quantity, avg cost)
- `POST /api/holdings` — Buy stocks (creates transaction, updates avg cost)
- `POST /api/holdings/sell` — Sell stocks (creates sell transaction)
- `GET /api/transactions` — Get transaction history with filtering
- `GET /api/portfolio` — Get portfolio holdings grouped by ticker

### Portfolio Analysis

- `GET /api/summary` — Portfolio summary (cost basis, market value, P&L per ticker and total)
- `GET /api/performance` — Portfolio value over time (for charting)
- `GET /api/win-rate` — Win rate statistics (% of profitable sells)

### Price Data

- `GET /api/price/<ticker>` — Get current price for a ticker from Yahoo Finance
- `GET /api/ticker/<ticker>` — Get detailed ticker info (sector, industry, P/E ratio, etc.)

See Swagger UI at http://localhost:5001/apidocs for full documentation.

## Running Tests

```bash
pytest
```

## Project Layout

```
portfolio-manager/
  app/
    __init__.py              # app factory
    config.py                # DB config (MySQL)
    models.py                # SQLAlchemy models (User, Transaction, PriceHistory)
    routes.py                # REST API endpoints
    performance.py           # Portfolio calculations (avg cost, P&L, win rate)
    price_backfill.py        # Yahoo Finance price fetching
  data_migrations/
    001_add_transactions.sql # Sample transaction data
    003_add_price_history.sql # Sample price history data
    README.md                # Data migration guide
  static/
    css/style.css
    js/app.js
  templates/
    index.html
  tests/
    test_api.py
    test_pnl.py
    test_performance.py
  .env                       # Database connection (create this)
  run.py                     # Application entry point
  requirements.txt           # Python dependencies
```

## Troubleshooting

### MySQL Connection Error

- Make sure MySQL is running: `brew services start mysql`
- Check `.env` has correct `DATABASE_URL`
- Verify database exists: `mysql -u root -e "SHOW DATABASES;"`

### Missing Price History

- Performance chart needs price history to calculate portfolio value
- Load sample data from `data_migrations/003_add_price_history.sql`

### Port Already in Use

- Change port in `run.py` (default: 5001)
- Or kill existing process: `lsof -ti:5001 | xargs kill -9`

## Design & Architecture

### Data Model

**Transactions** (source of truth)
- `id`, `action` (buy/sell), `ticker`, `quantity`, `price`, `transaction_date`
- All buys and sells are recorded as immutable audit trail

**Price History**
- `id`, `ticker`, `price_date`, `close_price`
- Used for portfolio value calculations and performance charting

**Holdings** (calculated, not stored)
- Derived from transaction history using average-cost method
- Each holding shows: shares owned, average cost, current price, cost basis, market value, P&L

### Key Concepts

**Average-Cost Method**
- When you buy more shares, the average cost per share is recalculated
- When you sell, P&L is calculated against the average cost (not the specific purchase price)
- Formula: `(old_avg_cost × old_qty + new_buy_price × new_qty) / total_qty`

**Cost Basis**
- Total amount invested in current holdings
- Calculated as: `quantity × average_cost`
- Updates when you buy (affects avg cost) or sell (affects quantity)

**Unrealized P&L**
- Profit/loss if you sold all shares at current market price
- Calculated as: `market_value - cost_basis`
- Updates daily with price changes and on buy/sell transactions

**Realized P&L**
- Actual profit/loss from completed sales
- Only calculated when you sell: `(sale_price - avg_cost) × qty_sold`

**Win Rate**
- Percentage of sell transactions that were profitable (P&L > 0)
- Break-even sales (P&L = 0) are not counted as wins


## Presentation link (canva)
- https://canva.link/r099y0sicompl10
