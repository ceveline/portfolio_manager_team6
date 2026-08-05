import time
from datetime import date, datetime, timedelta

import pytest

from app import create_app, db
from app.models import Transaction, PriceHistory
from app import performance as perf


@pytest.fixture(scope="module")
def test_app():
    # Create an app configured for testing using an in-memory SQLite DB
    class TestConfig:
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        SQLALCHEMY_TRACK_MODIFICATIONS = False

    app = create_app(config_object=TestConfig)

    with app.app_context():
        # create tables and yield app for tests
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def seed_large_dataset(num_tickers=20, days=365):
    """Seed the database with synthetic price history and transactions.
    - num_tickers: how many distinct tickers
    - days: number of days of price history
    """
    tickers = [f"T{i:03d}" for i in range(num_tickers)]
    start = date.today() - timedelta(days=days - 1)

    # Prices: each ticker gets a simple sinusoidal-like sequence
    price_rows = []
    for t_idx, ticker in enumerate(tickers):
        base = 10 + (t_idx % 10)  # vary base price a bit
        for d in range(days):
            pd = start + timedelta(days=d)
            price = round(base + ((d % 30) - 15) * 0.1 + (t_idx * 0.01), 2)
            price_rows.append(PriceHistory(ticker=ticker, price_date=pd, close_price=price))

    db.session.bulk_save_objects(price_rows)

    # Transactions: for each ticker, create buys every ~10 days and occasional sells
    tx_rows = []
    for t_idx, ticker in enumerate(tickers):
        qty = 10 + (t_idx % 5)
        for d in range(0, days, 10):
            # store transaction_date as a date to match price_date usage in tests
            tx_date = start + timedelta(days=d)
            price = 10 + (t_idx % 10) + (d % 30) * 0.02
            tx_rows.append(
                Transaction(action="buy", ticker=ticker, quantity=qty, price=price, transaction_date=tx_date)
            )
        # add a sell in the middle
        sell_day = days // 2
        sell_date = start + timedelta(days=sell_day)
        tx_rows.append(Transaction(action="sell", ticker=ticker, quantity=qty // 2, price=price + 1.0, transaction_date=sell_date))

    db.session.bulk_save_objects(tx_rows)
    db.session.commit()

    return tickers, start, start + timedelta(days=days - 1)


def test_portfolio_value_series_performance(test_app):
    with test_app.app_context():
        tickers, start, end = seed_large_dataset(num_tickers=20, days=365)

        # Measure runtime for portfolio_value_series
        t0 = time.perf_counter()
        series = perf.portfolio_value_series(start, end, tickers=tickers)
        dur = time.perf_counter() - t0

        # Basic correctness checks
        assert isinstance(series, list)
        assert series, "Expected non-empty series"

        # Performance assertion: should complete reasonably quickly
        assert dur < 3.0, f"portfolio_value_series too slow: {dur:.2f}s"


def test_replay_and_winrate_performance(test_app):
    with test_app.app_context():
        # Reuse existing data (seeded by previous test run) if present; otherwise seed smaller set
        if not Transaction.query.first():
            tickers, start, end = seed_large_dataset(num_tickers=10, days=180)
        else:
            tickers = [r[0] for r in db.session.query(Transaction.ticker).distinct().all()]

        # Measure replay_position across all tickers
        t0 = time.perf_counter()
        for t in tickers:
            _ = perf.replay_position(t)
        dur_replay = time.perf_counter() - t0

        # Measure calculate_win_rate
        t1 = time.perf_counter()
        win = perf.calculate_win_rate()
        dur_win = time.perf_counter() - t1

        # Basic sanity checks
        assert "win_rate_pct" in win

        # Allow reasonable thresholds
        assert dur_replay < 1.5, f"replay_position loop too slow: {dur_replay:.2f}s"
        assert dur_win < 1.0, f"calculate_win_rate too slow: {dur_win:.2f}s"


def test_portfolio_summary_performance(test_app):
    with test_app.app_context():
        # Prepare current prices map for tickers from transactions
        if not Transaction.query.first():
            tickers, _, _ = seed_large_dataset(num_tickers=10, days=180)
        else:
            tickers = [r[0] for r in db.session.query(Transaction.ticker).distinct().all()]

        current_prices = {t: 12.34 for t in tickers}

        t0 = time.perf_counter()
        summary = perf.portfolio_summary(current_prices)
        dur = time.perf_counter() - t0

        assert "positions" in summary
        assert dur < 1.0, f"portfolio_summary too slow: {dur:.2f}s"
