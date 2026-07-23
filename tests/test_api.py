import pytest

from app import create_app, db


@pytest.fixture
def client():
    app = create_app("app.config.Config")
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite:///:memory:", TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()

    with app.test_client() as client:
        yield client


def test_empty_portfolio(client):
    res = client.get("/api/portfolio")
    assert res.status_code == 200
    assert res.get_json() == []


def test_buy_and_list(client):
    res = client.post(
        "/api/holdings",
        json={"ticker": "aapl", "quantity": 5, "purchase_price": 100.0},
    )
    assert res.status_code == 201
    assert res.get_json()["ticker"] == "AAPL"

    res = client.get("/api/portfolio")
    assert len(res.get_json()) == 1


def test_buy_missing_fields(client):
    res = client.post("/api/holdings", json={"ticker": "AAPL"})
    assert res.status_code == 400


def test_sell(client):
    create_res = client.post(
        "/api/holdings",
        json={"ticker": "TSLA", "quantity": 2, "purchase_price": 200.0},
    )
    holding_id = create_res.get_json()["id"]

    del_res = client.delete(f"/api/holdings/{holding_id}")
    assert del_res.status_code == 204

    res = client.get("/api/portfolio")
    assert res.get_json() == []


def test_filter_transactions(client):
    buy_res = client.post(
        "/api/holdings",
        json={
            "ticker": "AAPL",
            "quantity": 5,
            "purchase_price": 100.0,
            "purchase_date": "2026-07-20",
        },
    )
    assert buy_res.status_code == 201

    sell_res = client.post(
        "/api/holdings",
        json={
            "ticker": "TSLA",
            "quantity": 3,
            "purchase_price": 200.0,
            "purchase_date": "2026-07-21",
        },
    )
    assert sell_res.status_code == 201

    holding_id = sell_res.get_json()["id"]
    delete_res = client.delete(f"/api/holdings/{holding_id}?quantity=2&sell_date=2026-07-22")
    assert delete_res.status_code == 204

    buy_filter = client.get("/api/transactions?action=buy")
    assert buy_filter.status_code == 200
    assert len(buy_filter.get_json()) == 2
    assert {item["ticker"] for item in buy_filter.get_json()} == {"AAPL", "TSLA"}

    ticker_filter = client.get("/api/transactions?ticker=TSLA")
    assert ticker_filter.status_code == 200
    assert len(ticker_filter.get_json()) == 2
    assert {item["action"] for item in ticker_filter.get_json()} == {"buy", "sell"}

    quantity_filter = client.get("/api/transactions?quantity=2")
    assert quantity_filter.status_code == 200
    assert len(quantity_filter.get_json()) == 1
    assert quantity_filter.get_json()[0]["quantity"] == 2

    date_filter = client.get("/api/transactions?date=2026-07-22")
    assert date_filter.status_code == 200
    assert len(date_filter.get_json()) == 1

    price_filter = client.get("/api/transactions?price=100")
    assert price_filter.status_code == 200
    assert len(price_filter.get_json()) == 1
    assert price_filter.get_json()[0]["price"] == 100.0


def test_comparison_and_range_filters(client):
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

    quantity_filter = client.get("/api/transactions?quantity=>=4")
    assert quantity_filter.status_code == 200
    assert len(quantity_filter.get_json()) == 2

    price_filter = client.get("/api/transactions?price=>=100")
    assert price_filter.status_code == 200
    assert len(price_filter.get_json()) == 2

    range_filter = client.get("/api/transactions?price_range=100-500")
    assert range_filter.status_code == 200
    assert len(range_filter.get_json()) == 2


def test_consolidated_avg_price_is_weighted_by_quantity(client):
    client.post(
        "/api/holdings",
        json={"ticker": "AAPL", "quantity": 1, "purchase_price": 100.0, "purchase_date": "2026-07-20"},
    )
    client.post(
        "/api/holdings",
        json={"ticker": "AAPL", "quantity": 3, "purchase_price": 200.0, "purchase_date": "2026-07-21"},
    )

    res = client.get("/api/consolidated")
    assert res.status_code == 200
    payload = res.get_json()
    assert len(payload) == 1
    assert payload[0]["ticker"] == "AAPL"
    assert payload[0]["avg_price"] == 175.0
