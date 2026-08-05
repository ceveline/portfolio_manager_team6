# Data Migrations

Seed scripts to populate the database with sample data for testing and development.

## Prerequisites

- MySQL server must be running
- Database created: `mysql -u root -e "CREATE DATABASE IF NOT EXISTS portfolio_manager;"`
- Flask app tables created: `python -c "from app import create_app, db; app = create_app(); with app.app_context(): db.create_all()"`

## Running the migrations

**Option 1: Individual scripts (for transactions and price history)**

```bash
mysql -u root portfolio_manager < data_migrations/001_add_transactions.sql
mysql -u root portfolio_manager < data_migrations/003_add_price_history.sql
```

**Option 2: Using the convenience script**

```bash
bash data_migrations/run_all.sh
```

This will run all available migrations in order with progress feedback.

## What each script does

1. **001_add_transactions.sql** - Creates biweekly buy transactions from Feb 2026 to July 2026
   - **AAPL:** 13 buys of 10 shares each (130 total) at varying prices ($248.73 - $338.19)
   - **GOOGL:** 13 buys of 10 shares each (130 total) at varying prices ($295.59 - $396.54)
   - All purchases use actual closing prices from the price history table
   - Purchases occur every 2 weeks over a 6-month period

2. **003_add_price_history.sql** - Creates daily price history for 1 year
   - Each ticker has multiple data points spanning the year
   - Prices show realistic growth patterns
   - Required for portfolio performance charts

## Important Notes

- Dates use `CURDATE()` so data stays current relative to today
- **Duplicates:** Running scripts multiple times will create duplicate records. To reset, you may need to clear the tables manually:
  ```bash
  mysql -u root portfolio_manager -e "DELETE FROM transactions; DELETE FROM price_history;"
  ```
- The transaction data is the source of truth; holdings are calculated from transactions
- Price history is required for performance calculations and charts

## Troubleshooting

If you see an error like "Table already exists":
- This is expected if data was already loaded
- To reload, delete records first (see above)

If a migration fails:
- Verify MySQL is running: `brew services start mysql`
- Check database exists: `mysql -u root -e "SHOW DATABASES;"`
- Verify tables exist: `mysql -u root portfolio_manager -e "SHOW TABLES;"`
