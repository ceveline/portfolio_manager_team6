-- Add holdings based on the transactions created by 001_add_transactions.sql
-- Current holdings after all biweekly purchases

-- AAPL: 13 purchases × 10 shares = 130 shares
-- Average purchase price: (275.977 + 260.34 + 260.05 + 248.731 + 255.684 + 269.981 + 279.882 + 300.23 + 306.31 + 296.42 + 289.36 + 327.5 + 338.19) / 13 = 277.587
INSERT INTO holdings (ticker, quantity, purchase_price, purchase_date)
VALUES ('AAPL', 130, 277.587, '2026-07-29');

-- GOOGL: 13 purchases × 10 shares = 130 shares
-- Average purchase price: (332.607 + 302.456 + 300.489 + 306.947 + 295.593 + 341.476 + 385.46 + 396.543 + 376.145 + 369.35 + 357.37 + 370.92 + 336.71) / 13 = 344.005
INSERT INTO holdings (ticker, quantity, purchase_price, purchase_date)
VALUES ('GOOGL', 130, 344.005, '2026-07-29');
