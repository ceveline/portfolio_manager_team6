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
