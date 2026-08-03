# Data Migrations

Seed scripts to populate the database with sample data for testing and development.

## Running the migrations

Run all three in order:

```bash
mysql -u root portfolio_manager < data_migrations/001_add_transactions.sql
mysql -u root portfolio_manager < data_migrations/002_add_holdings.sql
mysql -u root portfolio_manager < data_migrations/003_add_price_history.sql
```

Or use the convenience script:

```bash
./data_migrations/run_all.sh
```

## What each script does

1. **001_add_transactions.sql** - Creates buy/sell transactions dating back 1 year
   - AAPL: Buy 100 (1y ago), Sell 25 (6mo ago)
   - MSFT: Buy 50 (1y ago), Sell 20 (1mo ago)
   - GOOGL: Buy 30 (6mo ago)
   - TSLA: Buy 75 (3mo ago)
   - AMZN: Buy 50 (1 week ago)

2. **002_add_holdings.sql** - Creates holdings based on net transactions
   - AAPL: 75 shares (100 - 25)
   - MSFT: 30 shares (50 - 20)
   - GOOGL: 30 shares
   - TSLA: 75 shares
   - AMZN: 50 shares

3. **003_add_price_history.sql** - Creates daily price history for 1 year
   - Each ticker has 12 data points spanning the year
   - Prices show realistic growth patterns

## Notes

- Dates are relative to today using `CURDATE()` so they stay current
- All three scripts should be run in order for the data to be complete
- You can run them multiple times if needed (will create duplicates)
