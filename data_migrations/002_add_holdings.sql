-- Add holdings based on the transactions created by 001_add_transactions.sql
-- Calculate net quantity for each ticker (buy - sell)

-- AAPL: 100 bought, 25 sold = 75 shares at avg price of $150
INSERT INTO holdings (ticker, quantity, purchase_price, purchase_date)
VALUES ('AAPL', 75, 150.00, DATE_SUB(CURDATE(), INTERVAL 1 YEAR));

-- MSFT: 50 bought, 20 sold = 30 shares at $300
INSERT INTO holdings (ticker, quantity, purchase_price, purchase_date)
VALUES ('MSFT', 30, 300.00, DATE_SUB(CURDATE(), INTERVAL 1 YEAR));

-- GOOGL: 30 bought, 0 sold = 30 shares at $2500
INSERT INTO holdings (ticker, quantity, purchase_price, purchase_date)
VALUES ('GOOGL', 30, 2500.00, DATE_SUB(CURDATE(), INTERVAL 6 MONTH));

-- TSLA: 75 bought, 0 sold = 75 shares at $800
INSERT INTO holdings (ticker, quantity, purchase_price, purchase_date)
VALUES ('TSLA', 75, 800.00, DATE_SUB(CURDATE(), INTERVAL 3 MONTH));

-- AMZN: 50 bought, 0 sold = 50 shares at $3200
INSERT INTO holdings (ticker, quantity, purchase_price, purchase_date)
VALUES ('AMZN', 50, 3200.00, DATE_SUB(CURDATE(), INTERVAL 1 WEEK));
