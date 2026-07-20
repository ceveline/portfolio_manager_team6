from datetime import date

from app import db


class Holding(db.Model):
    """A single stock position held in the (one and only) portfolio.

    Kept deliberately minimal for the MVP - fields can grow as
    requirements evolve (see project notes: start small).
    """

    __tablename__ = "holdings"

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False, index=True)
    quantity = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.Date, nullable=False, default=date.today)

    def to_dict(self):
        return {
            "id": self.id,
            "ticker": self.ticker,
            "quantity": self.quantity,
            "purchase_price": self.purchase_price,
            "purchase_date": self.purchase_date.isoformat(),
        }


class Transaction(db.Model):
    """Transaction history for all buy/sell actions."""

    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(4), nullable=False)  # 'buy' or 'sell'
    ticker = db.Column(db.String(10), nullable=False, index=True)
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    transaction_date = db.Column(db.Date, nullable=False, default=date.today)

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "ticker": self.ticker,
            "quantity": self.quantity,
            "price": self.price,
            "transaction_date": self.transaction_date.isoformat(),
        }
