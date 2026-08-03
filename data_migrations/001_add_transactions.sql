-- Add sample transactions for historical data
-- This script adds transactions from 1 year ago, 6 months ago, and 3 months ago

-- 1 year ago: Buy 100 shares of AAPL at $150
INSERT INTO transactions (action, ticker, quantity, price, transaction_date)
VALUES ('buy', 'AAPL', 100, 150.00, DATE_SUB(NOW(), INTERVAL 1 YEAR));

-- 1 year ago: Buy 50 shares of MSFT at $300
INSERT INTO transactions (action, ticker, quantity, price, transaction_date)
VALUES ('buy', 'MSFT', 50, 300.00, DATE_SUB(NOW(), INTERVAL 1 YEAR));

-- 6 months ago: Buy 30 shares of GOOGL at $2500
INSERT INTO transactions (action, ticker, quantity, price, transaction_date)
VALUES ('buy', 'GOOGL', 30, 2500.00, DATE_SUB(NOW(), INTERVAL 6 MONTH));

-- 6 months ago: Sell 25 shares of AAPL at $160
INSERT INTO transactions (action, ticker, quantity, price, transaction_date)
VALUES ('sell', 'AAPL', 25, 160.00, DATE_SUB(NOW(), INTERVAL 6 MONTH));

-- 3 months ago: Buy 75 shares of TSLA at $800
INSERT INTO transactions (action, ticker, quantity, price, transaction_date)
VALUES ('buy', 'TSLA', 75, 800.00, DATE_SUB(NOW(), INTERVAL 3 MONTH));

-- 1 month ago: Sell 20 shares of MSFT at $320
INSERT INTO transactions (action, ticker, quantity, price, transaction_date)
VALUES ('sell', 'MSFT', 20, 320.00, DATE_SUB(NOW(), INTERVAL 1 MONTH));

-- 1 week ago: Buy 50 shares of AMZN at $3200
INSERT INTO transactions (action, ticker, quantity, price, transaction_date)
VALUES ('buy', 'AMZN', 50, 3200.00, DATE_SUB(NOW(), INTERVAL 1 WEEK));
