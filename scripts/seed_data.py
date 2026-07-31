import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta

from app import create_app, db
from app.models import Holding, Transaction, PriceHistory


app = create_app()

with app.app_context():

    # Clear old test data (optional)
    db.session.query(Transaction).delete()
    db.session.query(Holding).delete()
    db.session.query(PriceHistory).delete()

    today = datetime.now()

    # Fake holdings
    holdings = [
        Holding(
            ticker="AAPL",
            quantity=10,
            purchase_price=180.00,
            purchase_date=(today - timedelta(days=365)).date()
        ),
        Holding(
            ticker="MSFT",
            quantity=5,
            purchase_price=350.00,
            purchase_date=(today - timedelta(days=240)).date()
        ),
        Holding(
            ticker="NVDA",
            quantity=20,
            purchase_price=120.00,
            purchase_date=(today - timedelta(days=120)).date()
        ),
    ]

    db.session.add_all(holdings)

    # Fake transaction history
    transactions = [
        Transaction(
            action="buy",
            ticker="AAPL",
            quantity=10,
            price=180.00,
            transaction_date=today - timedelta(days=365)
        ),
        Transaction(
            action="buy",
            ticker="MSFT",
            quantity=5,
            price=350.00,
            transaction_date=today - timedelta(days=240)
        ),
        Transaction(
            action="sell",
            ticker="AAPL",
            quantity=3,
            price=200.00,
            transaction_date=today - timedelta(days=180)
        ),
        Transaction(
            action="buy",
            ticker="NVDA",
            quantity=20,
            price=120.00,
            transaction_date=today - timedelta(days=120)
        ),
    ]

    db.session.add_all(transactions)

    # Fake price history
    prices = [
        PriceHistory(
            ticker="AAPL",
            price_date=(today - timedelta(days=365)).date(),
            close_price=180.00
        ),
        PriceHistory(
            ticker="AAPL",
            price_date=(today - timedelta(days=180)).date(),
            close_price=200.00
        ),
        PriceHistory(
            ticker="MSFT",
            price_date=(today - timedelta(days=240)).date(),
            close_price=350.00
        ),
        PriceHistory(
            ticker="NVDA",
            price_date=(today - timedelta(days=120)).date(),
            close_price=120.00
        ),
    ]

    db.session.add_all(prices)

    db.session.commit()

    print("Fake data inserted successfully!")