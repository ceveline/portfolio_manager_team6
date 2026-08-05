"""Test portfolio P&L calculations against manual example."""
from datetime import date, timedelta
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


def test_pnl_after_each_transaction(app_context):
    """Verify P&L calculations after each transaction.

    Manual example:
    Start: $1000 cash, 0 shares

    1. Buy 100 @ $10
       - Shares: 100, Avg Cost: $10, Realized P/L: $0, Unrealized P/L: $0

    2. Price at $15, Sell 50
       - Shares: 50, Avg Cost: $10
       - Realized P/L: 50 × (15-10) = $250
       - Unrealized P/L @ $15: 50 × (15-10) = $250
       - Total P/L: $500

    3. Price at $10 (no transaction)
       - Shares: 50, Avg Cost: $10
       - Realized P/L: $250
       - Unrealized P/L @ $10: 50 × (10-10) = $0
       - Total P/L: $250

    4. Price at $20 (no transaction)
       - Shares: 50, Avg Cost: $10
       - Realized P/L: $250
       - Unrealized P/L @ $20: 50 × (20-10) = $500
       - Total P/L: $750

    5. Buy 10 @ $25
       - Shares: 60, Avg Cost: (50×10 + 10×25)/60 = $12.50
       - Realized P/L: $250
       - Unrealized P/L @ $25: 60 × (25-12.50) = $750
       - Total P/L: $1000

    6. Price at $15 (no transaction)
       - Shares: 60, Avg Cost: $12.50
       - Realized P/L: $250
       - Unrealized P/L @ $15: 60 × (15-12.50) = $150
       - Total P/L: $400

    7. Price at $20 (no transaction)
       - Shares: 60, Avg Cost: $12.50
       - Realized P/L: $250
       - Unrealized P/L @ $20: 60 × (20-12.50) = $450
       - Total P/L: $700

    8. Sell 20 @ $15
       - Shares: 40, Avg Cost: $12.50
       - Realized P/L: 250 + 20×(15-12.50) = $300
       - Unrealized P/L @ $15: 40 × (15-12.50) = $100
       - Total P/L: $400

    9. Price at $30
       - Shares: 40, Avg Cost: $12.50
       - Realized P/L: $300
       - Unrealized P/L @ $30: 40 × (30-12.50) = $700
       - Total P/L: $1000
    """
    base_date = date(2026, 1, 1)

    # =========== DAY 1: no transactions ===========
    print(f"\n{'='*90}")
    print(f"DAY 1: Starting state")
    print(f"{'='*90}")

    # Verify no positions yet
    tickers = perf.all_tickers()
    assert len(tickers) == 0, f"Day 1: expected no tickers, got {tickers}"

    # Portfolio summary - no positions yet
    summary = perf.portfolio_summary({})
    assert len(summary["positions"]) == 0, "No positions on Day 1"
    assert summary["total_cost_basis"] == 0.0
    assert summary["total_market_value"] == 0.0
    assert summary["total_realized_pnl"] == 0.0
    assert summary["total_unrealized_pnl"] == 0.0
    assert summary["total_return_pct"] == 0.0
    # Verify: unrealized + realized = total
    total_pnl = summary["total_unrealized_pnl"] + summary["total_realized_pnl"]
    assert total_pnl == 0.0, f"Total P/L check: {summary['total_unrealized_pnl']} + {summary['total_realized_pnl']} = {total_pnl}"

    print(f"✓ Day 1 | Shares: 0 | Avg Cost: $0 | Realized P/L: $0 | Unrealized: $0")

    # =========== DAY 2: Buy 100 @ $10 ===========
    tx1 = Transaction(action="buy", ticker="TEST", quantity=100, price=10,
                     transaction_date=base_date + timedelta(days=1))
    db.session.add(tx1)
    db.session.commit()

    pos = perf.replay_position("TEST")
    assert pos["shares_held"] == 100.0
    assert pos["avg_cost"] == 10.0
    assert pos["realized_pnl"] == 0.0

    summary = perf.portfolio_summary({"TEST": 10})
    assert len(summary["positions"]) == 1
    position = summary["positions"][0]
    assert position["shares_held"] == 100.0
    assert position["avg_cost"] == 10.0
    assert position["unrealized_pnl"] == 0.0
    assert position["realized_pnl"] == 0.0
    print(f"✓ Day 2 | Shares: 100 | Avg Cost: $10.00 | Realized P/L: $0 | Unrealized: $0")


    # =========== DAY 3: Sell 50 @ $15 ===========
    tx2 = Transaction(action="sell", ticker="TEST", quantity=50, price=15,
                     transaction_date=base_date + timedelta(days=2))
    db.session.add(tx2)
    db.session.commit()

    pos = perf.replay_position("TEST")
    assert pos["shares_held"] == 50.0
    assert pos["avg_cost"] == 10.0
    assert pos["realized_pnl"] == 250.0

    summary = perf.portfolio_summary({"TEST": 15})
    assert len(summary["positions"]) == 1
    position = summary["positions"][0]
    assert position["shares_held"] == 50.0
    assert position["avg_cost"] == 10.0
    assert position["unrealized_pnl"] == 250.0
    assert position["realized_pnl"] == 250.0
    print(f"✓ Day 3 | Shares: 50 | Avg Cost: $10.00 | Realized P/L: $250 | Unrealized: $250")

    # =========== DAY 4-5: Price changes ===========
    # Day 4: Price at $10
    summary = perf.portfolio_summary({"TEST": 10})
    assert len(summary["positions"]) == 1
    position = summary["positions"][0]
    assert position["shares_held"] == 50.0
    assert position["avg_cost"] == 10.0
    assert position["unrealized_pnl"] == 0.0
    assert position["realized_pnl"] == 250.0

    print(f"✓ Day 4 | Shares: 50 | Avg Cost: $10.00 | Realized P/L: $250 | Unrealized: $0")

    # Day 5: Price at $20
    summary = perf.portfolio_summary({"TEST": 20})
    position = summary["positions"][0]
    assert position["unrealized_pnl"] == 500.0
    total_pnl = position["realized_pnl"] + position["unrealized_pnl"]
    assert total_pnl == 750.0
    # Verify: unrealized + realized = total
    total_pnl = summary["total_unrealized_pnl"] + summary["total_realized_pnl"]
    assert total_pnl == 750.0, f"Total P/L check: {summary['total_unrealized_pnl']} + {summary['total_realized_pnl']} = {total_pnl}"
    print(f"✓ Day 5 | Shares: 50 | Avg Cost: $10.00 | Realized P/L: $250 | Unrealized: $500")

    # =========== DAY 6: Buy 10 @ $25 ===========
    tx3 = Transaction(action="buy", ticker="TEST", quantity=10, price=25,
                     transaction_date=base_date + timedelta(days=5))
    db.session.add(tx3)
    db.session.commit()

    pos = perf.replay_position("TEST")
    assert pos["shares_held"] == 60.0
    assert abs(pos["avg_cost"] - 12.50) < 0.01
    assert pos["realized_pnl"] == 250.0

    summary = perf.portfolio_summary({"TEST": 25})
    assert len(summary["positions"]) == 1
    position = summary["positions"][0]
    assert position["shares_held"] == 60.0
    assert abs(position["avg_cost"] - 12.50) < 0.01
    assert position["unrealized_pnl"] == 750.0
    assert position["realized_pnl"] == 250.0
    print(f"✓ Day 6 | Shares: 60 | Avg Cost: $12.50 | Realized P/L: $250 | Unrealized: $750")

    # =========== DAY 7-8: Price changes ===========
    # Day 7: Price at $15
    summary = perf.portfolio_summary({"TEST": 15})
    position = summary["positions"][0]
    assert position["unrealized_pnl"] == 150.0
    total_pnl = position["realized_pnl"] + position["unrealized_pnl"]
    assert total_pnl == 400.0
    # Verify: unrealized + realized = total
    total_pnl = summary["total_unrealized_pnl"] + summary["total_realized_pnl"]
    assert total_pnl == 400.0, f"Total P/L check: {summary['total_unrealized_pnl']} + {summary['total_realized_pnl']} = {total_pnl}"
    print(f"✓ Day 7 | Shares: 60 | Avg Cost: $12.50 | Realized P/L: $250 | Unrealized: $150")

    # Day 8: Price at $20
    summary = perf.portfolio_summary({"TEST": 20})
    position = summary["positions"][0]
    assert position["unrealized_pnl"] == 450.0
    print(f"✓ Day 8 | Shares: 60 | Avg Cost: $12.50 | Realized P/L: $250 | Unrealized: $450")

    # =========== DAY 9: Sell 20 @ $15 ===========
    tx4 = Transaction(action="sell", ticker="TEST", quantity=20, price=15,
                     transaction_date=base_date + timedelta(days=8))
    db.session.add(tx4)
    db.session.commit()

    pos = perf.replay_position("TEST")
    assert pos["shares_held"] == 40.0
    assert abs(pos["avg_cost"] - 12.50) < 0.01
    assert pos["realized_pnl"] == 300.0

    summary = perf.portfolio_summary({"TEST": 15})
    assert len(summary["positions"]) == 1
    position = summary["positions"][0]
    assert position["shares_held"] == 40.0
    assert abs(position["avg_cost"] - 12.50) < 0.01
    assert position["unrealized_pnl"] == 100.0
    assert position["realized_pnl"] == 300.0
    print(f"✓ Day 9 | Shares: 40 | Avg Cost: $12.50 | Realized P/L: $300 | Unrealized: $100")

    # =========== DAY 10: Final price ===========
    summary = perf.portfolio_summary({"TEST": 30})
    assert len(summary["positions"]) == 1
    position = summary["positions"][0]
    assert position["shares_held"] == 40.0
    assert abs(position["avg_cost"] - 12.50) < 0.01
    assert position["current_price"] == 30.0
    assert position["realized_pnl"] == 300.0
    assert position["unrealized_pnl"] == 700.0
    assert abs(position["cost_basis"] - 500.0) < 0.01
    assert position["market_value"] == 1200.0
    print(f"✓ Day 10 | Shares: 40 | Avg Cost: $12.50 | Realized P/L: $300 | Unrealized: $700")

    print(f"\n{'='*90}")
    print("✓ All P&L calculations verified correct!")
    print(f"{'='*90}")
