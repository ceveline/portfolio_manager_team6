#!/bin/bash

# Run all data migration scripts in order

DB_USER="root"
DB_NAME="portfolio_manager"

echo "Running data migrations..."
echo ""

echo "1. Adding transactions..."
mysql -u $DB_USER $DB_NAME < data_migrations/001_add_transactions.sql
if [ $? -ne 0 ]; then
    echo "Error running 001_add_transactions.sql"
    exit 1
fi
echo "✓ Transactions added"
echo ""

echo "2. Adding price history..."
mysql -u $DB_USER $DB_NAME < data_migrations/003_add_price_history.sql
if [ $? -ne 0 ]; then
    echo "Error running 003_add_price_history.sql"
    exit 1
fi
echo "✓ Price history added"
echo ""

echo "All migrations completed successfully! ✓"
