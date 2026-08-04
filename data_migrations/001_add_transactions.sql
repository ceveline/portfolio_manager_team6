-- Insert transaction history
-- Biweekly purchases of 10 shares each for AAPL and GOOGL over 6 months (2026-02-04 to 2026-07-29)
-- Using actual closing prices from price_history table

INSERT INTO transactions (action, ticker, quantity, price, transaction_date) VALUES
('buy', 'AAPL', 10, 275.977, '2026-02-04'),
('buy', 'GOOGL', 10, 332.607, '2026-02-04'),
('buy', 'AAPL', 10, 260.34, '2026-02-19'),
('buy', 'GOOGL', 10, 302.456, '2026-02-19'),
('buy', 'AAPL', 10, 260.05, '2026-03-05'),
('buy', 'GOOGL', 10, 300.489, '2026-03-05'),
('buy', 'AAPL', 10, 248.731, '2026-03-19'),
('buy', 'GOOGL', 10, 306.947, '2026-03-19'),
('buy', 'AAPL', 10, 255.684, '2026-04-02'),
('buy', 'GOOGL', 10, 295.593, '2026-04-02'),
('buy', 'AAPL', 10, 269.981, '2026-04-17'),
('buy', 'GOOGL', 10, 341.476, '2026-04-17'),
('buy', 'AAPL', 10, 279.882, '2026-05-01'),
('buy', 'GOOGL', 10, 385.46, '2026-05-01'),
('buy', 'AAPL', 10, 300.23, '2026-05-15'),
('buy', 'GOOGL', 10, 396.543, '2026-05-15'),
('buy', 'AAPL', 10, 306.31, '2026-06-01'),
('buy', 'GOOGL', 10, 376.145, '2026-06-01'),
('buy', 'AAPL', 10, 296.42, '2026-06-15'),
('buy', 'GOOGL', 10, 369.35, '2026-06-15'),
('buy', 'AAPL', 10, 289.36, '2026-06-30'),
('buy', 'GOOGL', 10, 357.37, '2026-06-30'),
('buy', 'AAPL', 10, 327.5, '2026-07-15'),
('buy', 'GOOGL', 10, 370.92, '2026-07-15'),
('buy', 'AAPL', 10, 338.19, '2026-07-29'),
('buy', 'GOOGL', 10, 336.71, '2026-07-29');
