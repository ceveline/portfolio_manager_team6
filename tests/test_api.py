import pytest

from app import create_app, db


@pytest.fixture
def client():
    class TestConfig:
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        SQLALCHEMY_TRACK_MODIFICATIONS = False

    app = create_app(TestConfig)

    with app.app_context():
        db.drop_all()
        db.create_all()

        # Create default user for API tests
        from app.models import User
        user = User.query.filter_by(email="johndoe@gmail.com").first()
        if not user:
            db.session.add(
                User(
                    first_name="John",
                    last_name="Doe",
                    email="johndoe@gmail.com",
                    account_balance=110000
                )
            )
            db.session.commit()

    with app.test_client() as client:
        yield client


def test_empty_portfolio(client):
    """Test that empty portfolio returns empty list"""
    res = client.get("/api/portfolio")
    assert res.status_code == 200
    assert res.get_json() == []


def test_buy_returns_correct_response(client):
    """Test that buying stocks returns correct response"""
    res = client.post(
        "/api/holdings",
        json={"ticker": "AAPL", "quantity": 5, "purchase_price": 100.0},
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["ticker"] == "AAPL"
    assert data["quantity"] == 5
    assert data["purchase_price"] == 100.0


def test_buy_missing_fields(client):
    """Test that missing required fields returns 400"""
    res = client.post("/api/holdings", json={"ticker": "AAPL"})
    assert res.status_code == 400


def test_sell_returns_correct_response(client):
    """Test that selling stocks returns correct response"""
    # First buy
    buy_res = client.post(
        "/api/holdings",
        json={"ticker": "TSLA", "quantity": 2, "purchase_price": 200.0},
    )
    assert buy_res.status_code == 201

    # Then sell
    sell_res = client.post(
        "/api/holdings/sell",
        json={"ticker": "TSLA", "quantity": 1, "sell_price": 250.0},
    )
    assert sell_res.status_code == 201
    assert sell_res.get_json()["ticker"] == "TSLA"


def test_get_transactions(client):
    """Test getting transaction history"""
    # Create a transaction
    client.post(
        "/api/holdings",
        json={"ticker": "AAPL", "quantity": 5, "purchase_price": 100.0, "purchase_date": "2026-07-20"},
    )

    # Get transactions
    res = client.get("/api/transactions")
    assert res.status_code == 200
    transactions = res.get_json()
    assert len(transactions) >= 1
    assert transactions[0]["ticker"] == "AAPL"


def test_transactions_filtering(client):
    """Test filtering transactions by quantity"""
    # Create multiple transactions
    client.post(
        "/api/holdings",
        json={"ticker": "AAPL", "quantity": 6, "purchase_price": 80.0, "purchase_date": "2026-07-20"},
    )
    client.post(
        "/api/holdings",
        json={"ticker": "TSLA", "quantity": 4, "purchase_price": 120.0, "purchase_date": "2026-07-21"},
    )
    client.post(
        "/api/holdings",
        json={"ticker": "MSFT", "quantity": 2, "purchase_price": 300.0, "purchase_date": "2026-07-22"},
    )

    # Filter by quantity >= 4
    res = client.get("/api/transactions?quantity=>=4")
    assert res.status_code == 200
    transactions = res.get_json()
    # Should have 2 transactions: AAPL(6) and TSLA(4)
    assert len(transactions) == 2


def test_summary_endpoint(client):
    """Test portfolio summary endpoint"""
    client.post(
        "/api/holdings",
        json={"ticker": "AAPL", "quantity": 10, "purchase_price": 100.0},
    )

    res = client.get("/api/summary")
    assert res.status_code == 200
    summary = res.get_json()
    assert "positions" in summary
    assert "total_cost_basis" in summary
    assert "total_market_value" in summary
