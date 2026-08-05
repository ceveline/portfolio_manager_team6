"""Test portfolio P&L calculations against manual example."""
from datetime import date, timedelta
import csv
import os
import pytest
from app import create_app, db
from app.models import Transaction
from app import performance as perf


@pytest.fixture
def app_context():
    class TestConfig:
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        SQLALCHEMY_TRACK_MODIFICATIONS = False

    app = create_app(config_object=TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_pnl_final_state_only(app_context):
    """Verify final portfolio state at price $30 after all transactions."""
    base_date = date(2026, 1, 1)
    csv_path = os.path.join(os.path.dirname(__file__), "data_pnl.csv")

    # Load and execute all transactions from CSV
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        day_counter = 0
        for row in reader:
            if row["action"] == "start":
                continue

            action = row["action"]
            if action.startswith("+"):
                # Parse +100@10 format
                parts = action[1:].split("@")
                quantity = int(parts[0])
                price = float(parts[1])
                tx_action = "buy"

                tx = Transaction(
                    action=tx_action,
                    ticker="TEST",
                    quantity=quantity,
                    price=price,
                    transaction_date=base_date + timedelta(days=day_counter)
                )
                db.session.add(tx)
                day_counter += 1
            elif action.startswith("-"):
                # Parse -50@15 format
                parts = action[1:].split("@")
                quantity = int(parts[0])
                price = float(parts[1])
                tx_action = "sell"

                tx = Transaction(
                    action=tx_action,
                    ticker="TEST",
                    quantity=quantity,
                    price=price,
                    transaction_date=base_date + timedelta(days=day_counter)
                )
                db.session.add(tx)
                day_counter += 1
    db.session.commit()

    # Verify only final state at price $30
    summary = perf.portfolio_summary({"TEST": 30})
    position = summary["positions"][0]

    assert position["current_price"] == 30.0
    assert position["shares_held"] == 40.0
    assert abs(position["avg_cost"] - 12.50) < 0.01
    assert position["realized_pnl"] == 300.0
    assert position["unrealized_pnl"] == 700.0
    assert abs(position["cost_basis"] - 500.0) < 0.01
    assert position["market_value"] == 1200.0


def test_pnl_all_states(app_context):
    """Verify portfolio state at each step using CSV data."""
    base_date = date(2026, 1, 1)
    csv_path = os.path.join(os.path.dirname(__file__), "data_pnl.csv")

    # Load CSV and progressively add transactions, verifying at each step
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        day_counter = 0
        for row in reader:
            if row["action"] == "start":
                continue

            # Add transaction if present
            action = row["action"]
            if action.startswith("+"):
                parts = action[1:].split("@")
                quantity = int(parts[0])
                price = float(parts[1])
                tx_action = "buy"

                tx = Transaction(
                    action=tx_action,
                    ticker="TEST",
                    quantity=quantity,
                    price=price,
                    transaction_date=base_date + timedelta(days=day_counter)
                )
                db.session.add(tx)
                db.session.commit()
                day_counter += 1

            elif action.startswith("-"):
                parts = action[1:].split("@")
                quantity = int(parts[0])
                price = float(parts[1])
                tx_action = "sell"

                tx = Transaction(
                    action=tx_action,
                    ticker="TEST",
                    quantity=quantity,
                    price=price,
                    transaction_date=base_date + timedelta(days=day_counter)
                )
                db.session.add(tx)
                db.session.commit()
                day_counter += 1

            # Verify state at current price
            current_price = float(row["current_price"]) if row["current_price"] != "-" else None
            if current_price is None:
                continue

            summary = perf.portfolio_summary({"TEST": current_price})

            if not summary["positions"]:
                assert row["shares"] == "0"
                assert row["realized_pnl"] == "0"
                continue

            position = summary["positions"][0]
            expected_shares = float(row["shares"])
            expected_avg_cost = float(row["avg_cost"])
            expected_realized = float(row["realized_pnl"])
            expected_unrealized = float(row["unrealized_pnl"])

            assert abs(position["shares_held"] - expected_shares) < 0.01, \
                f"Price ${current_price}: shares {position['shares_held']} != {expected_shares}"
            assert abs(position["avg_cost"] - expected_avg_cost) < 0.01, \
                f"Price ${current_price}: avg_cost {position['avg_cost']} != {expected_avg_cost}"
            assert abs(position["realized_pnl"] - expected_realized) < 0.01, \
                f"Price ${current_price}: realized_pnl {position['realized_pnl']} != {expected_realized}"
            assert abs(position["unrealized_pnl"] - expected_unrealized) < 0.01, \
                f"Price ${current_price}: unrealized_pnl {position['unrealized_pnl']} != {expected_unrealized}"
