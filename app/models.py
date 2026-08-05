from datetime import datetime

from app import db

class User(db.Model):
    """User account information."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    account_balance = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "account_balance": self.account_balance,
        }

class Transaction(db.Model):
    """Transaction history for all buy/sell actions."""

    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(4), nullable=False)  # 'buy' or 'sell'
    ticker = db.Column(db.String(10), nullable=False, index=True)
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "ticker": self.ticker,
            "quantity": self.quantity,
            "price": self.price,
            "transaction_date": self.transaction_date.isoformat(),
        }


class PriceHistory(db.Model):
    """Daily closing price per ticker, backfilled from yfinance."""

    __tablename__ = "price_history"
    __table_args__ = (
        db.UniqueConstraint("ticker", "price_date", name="uq_ticker_price_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False, index=True)
    price_date = db.Column(db.Date, nullable=False)
    close_price = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "ticker": self.ticker,
            "date": self.price_date.isoformat(),
            "close_price": self.close_price,
        }
