# Portfolio Manager

A stock portfolio management app that tracks holdings, transactions, and portfolio value in real-time.

## Features

- **Buy & Sell Stocks** — Add and remove multiple stocks from your portfolio
- **Auto Price Lookup** — Ticker dropdown with auto-populated current prices from AWS cached API
- **Portfolio Summary** — Live total portfolio value and share count in header
- **Consolidated View** — See total shares and average price per ticker
- **Transaction History** — Complete record of all buys and sells
- **Separate Holdings Tracking** — Preserve cost basis for each purchase

## Stack

- Python / Flask
- Flask-SQLAlchemy (SQLite)
- Plain HTML/JS frontend (no framework)
- Swagger docs via flasgger
- AWS cached price API (stock price data)
- yfinance (fallback stock price data)

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

Dependencies:

- **Flask** — Web framework
- **Flask-SQLAlchemy** — ORM for database
- **flasgger** — Swagger API documentation
- **requests** — HTTP client library
- **yfinance** — Fallback Yahoo Finance stock price API
- **pytest** — Testing framework

### 3. Run the Application

```bash
python run.py
```

The app starts in debug mode on `http://localhost:5001`

- **Frontend:** http://localhost:5001 (HTML/JS UI)
- **API:** http://localhost:5001/api/\* (REST endpoints)
- **Swagger UI:** http://localhost:5001/apidocs (interactive API docs)
- **Database:** `instance/portfolio.db` (created automatically on first run)

### 4. Database

SQLite database is created automatically in `instance/portfolio.db` with two tables:

- **holdings** — Current stock positions (each purchase is a separate record)
- **transactions** — Complete history of all buys and sells

No migration needed — Flask-SQLAlchemy creates tables on startup.

## Running tests

```bash
pytest
```

## Project layout

```
portfolio-manager/
  app/
    __init__.py         # app factory
    config.py           # config incl. DB URI
    models.py           # SQLAlchemy models (Holding, Transaction)
    routes.py           # REST API blueprint (/api/...)
  static/
    css/style.css
    js/app.js
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
  "quantity": 10,
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
