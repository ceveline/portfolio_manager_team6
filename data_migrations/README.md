# Data Migrations

Seed scripts to populate the database with sample data for testing and development.

## Prerequisites

- MySQL server must be running
- Database created: `mysql -u root -e "CREATE DATABASE IF NOT EXISTS portfolio_manager;"`
- Flask app tables created: `python -c "from app import create_app, db; app = create_app(); with app.app_context(): db.create_all()"`

## Running the migrations

```bash
# Load sample transactions
mysql -u root portfolio_manager < data_migrations/001_add_transactions.sql

# Load sample price history
mysql -u root portfolio_manager < data_migrations/003_add_price_history.sql
```

Both migrations should be run to get a complete working dataset with portfolio performance history.

## What each script does

1. **001_add_transactions.sql** - Creates sample buy and sell transactions
   - Multiple stock tickers with transactions spanning several months
   - Transactions use realistic prices and dates
   - Provides audit trail for testing portfolio calculations

2. **003_add_price_history.sql** - Creates daily price history for charting
   - Daily closing prices for each ticker
   - Covers the transaction date range to enable performance calculations
   - Required for portfolio value over time charts

## Important Notes

- **Transactions are the source of truth** — Holdings are calculated from transaction history using the average-cost method
- **Price history required** — Performance charts need price history data to calculate portfolio value over time
- **Duplicates:** Running scripts multiple times will create duplicate records. To reset:
  ```bash
  mysql -u root portfolio_manager -e "DELETE FROM transactions; DELETE FROM price_history;"
  ```
- Dates use `CURDATE()` so transactions stay current relative to today

## Troubleshooting

If you see an error like "Table already exists":

- This is expected if data was already loaded
- To reload, delete records first (see above)

If a migration fails:

- Verify MySQL is running: `brew services start mysql`
- Check database exists: `mysql -u root -e "SHOW DATABASES;"`
- Verify tables exist: `mysql -u root portfolio_manager -e "SHOW TABLES;"`
