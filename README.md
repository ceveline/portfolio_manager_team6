# Portfolio Manager

A stock portfolio management app that tracks holdings, transactions, and portfolio value in real-time.

## Team Members

1. Kelly Morilla
2. David Soriano
3. Ceveline Evangelista

## Features

- **Buy & Sell Stocks** — Add and remove multiple stocks from your portfolio
- **Auto Price Lookup** — Ticker dropdown with auto-populated current prices from AWS cached API
- **Portfolio Summary** — Live total portfolio value and share count in header
- **Consolidated View** — See total shares and average price per ticker
- **Transaction History** — Complete record of all buys and sells
- **Performance Chart** — Line chart showing portfolio value over time
- **Price History** — Historical daily prices for all tickers

## Stack

- Python / Flask
- Flask-SQLAlchemy (MySQL with PyMySQL)
- Plain HTML/JS frontend (no framework)
- Swagger docs via flasgger
- AWS cached price API (stock price data)
- yfinance (historical price backfilling)

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

- `GET /api/holdings` — List all current holdings
- `POST /api/holdings` — Buy stocks (creates transaction + holding)
- `DELETE /api/holdings/<ticker>` — Sell stocks (creates sell transaction)
- `GET /api/transactions` — Get transaction history (with filtering)
- `GET /api/consolidated` — Get consolidated view (grouped by ticker)

### Portfolio Analysis

- `GET /api/summary` — Portfolio summary (cost basis, P&L per ticker)
- `GET /api/performance` — Portfolio value over time (for charting)
- `GET /api/win-rate` — Win rate statistics

### Price Data

- `GET /api/price/<ticker>` — Get current price for a ticker
- `POST /api/price-history/backfill` — Backfill historical prices from Yahoo Finance
- `GET /api/price-history` — Get stored historical prices

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
    config.py                # DB config (MySQL support)
    models.py                # SQLAlchemy models
    routes.py                # REST API endpoints
    performance.py           # Portfolio calculations
    price_backfill.py        # Yahoo Finance price fetching
  data_migrations/
    001_add_transactions.sql # Sample transaction data
    002_add_holdings.sql     # Sample holdings data
    003_add_price_history.sql # Sample price history data
    README.md                # Data migration guide
  static/
    css/style.css
    js/app.js
  tests/
    # Test files
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
- Run price backfill: `curl -X POST http://localhost:5001/api/price-history/backfill`
- Or load sample data from `data_migrations/003_add_price_history.sql`

### Port Already in Use

- Change port in `run.py` (default: 5001)
- Or kill existing process: `lsof -ti:5001 | xargs kill -9`
  templates/
    index.html
  tests/
    test_api.py
  run.py
  requirements.txt
```

## API

| Method | Endpoint              | Description                                |
| ------ | --------------------- | ------------------------------------------ |
| GET    | /api/holdings         | List all individual holdings               |
| GET    | /api/consolidated     | Consolidated portfolio (grouped by ticker) |
| GET    | /api/holdings/`<id>`  | Single holding                             |
| POST   | /api/holdings         | Buy - create a holding                     |
| DELETE | /api/holdings/`<id>`  | Sell - reduce/remove a holding             |
| GET    | /api/transactions     | Transaction history                        |
| GET    | /api/price/`<ticker>` | Get current stock price                    |

### POST /api/holdings

Buy stocks:

```json
{
  "ticker": "AAPL",
  "quantity": 12,
  "purchase_price": 150.25,
  "purchase_date": "2026-07-20"
}
```

`purchase_date` is optional (defaults to today).

### DELETE /api/holdings/`<id>`

Sell stocks:

```
DELETE /api/holdings/1?quantity=5
```

`quantity` parameter is optional. If provided, only that quantity is sold and the holding is reduced. If not provided, the entire holding is deleted.

## Data Model

**Holding** — Individual stock purchase

- `id`, `ticker`, `quantity`, `purchase_price`, `purchase_date`

**Transaction** — Buy/sell record

- `id`, `action` (buy/sell), `ticker`, `quantity`, `price`, `transaction_date`

## Architecture

### Backend (Flask + SQLAlchemy)

**Routes** (`app/routes.py`):

- `GET /api/holdings` — Returns all individual holdings
- `GET /api/consolidated` — Groups holdings by ticker, calculates totals & average prices
- `GET /api/transactions` — Returns all buy/sell history
- `POST /api/holdings` — Create new holding (buy)
- `DELETE /api/holdings/<id>?quantity=X` — Reduce/delete holding (sell)
- `GET /api/price/<ticker>` — Fetch current price from AWS API or yfinance

**Models** (`app/models.py`):

- `Holding` — Individual purchase record (preserves cost basis)
- `Transaction` — Buy/sell action record (audit trail)

### Frontend (HTML + Vanilla JS)

**UI Sections** (`templates/index.html` + `static/js/app.js`):

1. **Header** — Portfolio summary (total value, total shares)
2. **Buy Stock** — Dropdown ticker selector → auto-fetch price → enter quantity & date
3. **Sell Stock** — Select from current holdings → enter quantity to sell → record transaction
4. **Portfolio** — Consolidated view (total shares + avg price per ticker)
5. **Transaction History** — All buys and sells with dates

**Real-time Updates**:

- Select ticker → fetch current price via `/api/price/<ticker>`
- Select stock to sell → display available quantity & current price
- Submit buy/sell → reload portfolio and transaction history

### Price Data Integration

**Price Fetching** (`GET /api/price/<ticker>`):

1. Try AWS cached price API (primary source)
2. Fall back to Yahoo Finance API via `yfinance` library
3. If both sources fail, return error

**Why Two Sources?**

- AWS cached API provides fast, reliable pricing with rate-limiting built-in
- yfinance provides fallback for any ticker not in AWS cache

### Database Schema

```sql
-- Holdings table: individual purchases (cost basis preserved)
CREATE TABLE holdings (
  id INTEGER PRIMARY KEY,
  ticker VARCHAR(10) NOT NULL,
  quantity FLOAT NOT NULL,
  purchase_price FLOAT NOT NULL,
  purchase_date DATE NOT NULL DEFAULT TODAY
);

-- Transactions table: audit trail of all trades
CREATE TABLE transactions (
  id INTEGER PRIMARY KEY,
  action VARCHAR(4) NOT NULL,  -- 'buy' or 'sell'
  ticker VARCHAR(10) NOT NULL,
  quantity FLOAT NOT NULL,
  price FLOAT NOT NULL,
  transaction_date DATE NOT NULL DEFAULT TODAY
);
```

## Design Decisions

- **Separate Holdings** — Each purchase stored separately to preserve cost basis for tax reporting
- **Consolidated View** — Frontend groups holdings by ticker with average purchase price calculated on-the-fly
- **Transaction History** — All buys and sells logged as immutable audit trail
- **Auto Price Lookup** — Stock price auto-populated when ticker selected; frontend handles UX
- **Dual Price Sources** — Uses AWS cached API for reliability and speed, with yfinance fallback for any ticker


## Presentation link (canva)
- https://canva.link/r099y0sicompl10
