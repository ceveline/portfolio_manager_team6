from datetime import datetime

from flasgger import swag_from
from flask import Blueprint, jsonify, request
import yfinance as yf

from app import db
from app.models import Holding, Transaction

api = Blueprint("api", __name__, url_prefix="/api")


def _parse_operator_value(raw_value):
    if raw_value is None:
        return "=", None

    value = str(raw_value).strip()
    if not value:
        return "=", None

    for operator in (">=", "<=", ">", "<", "="):
        if value.startswith(operator):
            return operator, value[len(operator):]

    return "=", value


@api.route("/price/<ticker>", methods=["GET"])
@swag_from(
    {
        "tags": ["Stock Data"],
        "summary": "Get current stock price from AWS cached Yahoo Finance API",
        "parameters": [
            {"name": "ticker", "in": "path", "type": "string", "required": True}
        ],
        "responses": {
            200: {"description": "Current stock price"},
            400: {"description": "Invalid ticker or unable to fetch price"}
        },
    }
)
def get_stock_price(ticker):
    import requests
    
    ticker_upper = ticker.upper()
    
    # Try AWS cached price API first
    try:
        aws_url = f"https://c4rm9elh30.execute-api.us-east-1.amazonaws.com/default/cachedPriceData?ticker={ticker_upper}"
        response = requests.get(aws_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                if "price" in data and data["price"] is not None:
                    return jsonify({"ticker": ticker_upper, "price": data["price"]}), 200

                price_data = data.get("price_data") or {}
                close_prices = price_data.get("close") or []
                if close_prices:
                    price = float(close_prices[-1])
                    return jsonify({"ticker": ticker_upper, "price": price}), 200
    except Exception:
        pass
    
    # Fall back to yfinance
    try:
        stock = yf.Ticker(ticker_upper)
        hist = stock.history(period='1d')
        if len(hist) > 0:
            price = float(hist['Close'].iloc[-1])
            return jsonify({"ticker": ticker_upper, "price": price}), 200
    except Exception:
        pass

    return jsonify({"error": f"Could not fetch price for {ticker}"}), 400


@api.route("/holdings", methods=["GET"])
@swag_from(
    {
        "tags": ["Holdings"],
        "summary": "List all holdings",
        "responses": {200: {"description": "List of holdings"}},
    }
)
def list_holdings():
    holdings = Holding.query.all()
    return jsonify([h.to_dict() for h in holdings]), 200


@api.route("/portfolio", methods=["GET"])
def get_portfolio():
    holdings = Holding.query.all()
    return jsonify([h.to_dict() for h in holdings]), 200


@api.route("/holdings/<int:holding_id>", methods=["GET"])
@swag_from(
    {
        "tags": ["Holdings"],
        "summary": "Get a single holding",
        "parameters": [
            {"name": "holding_id", "in": "path", "type": "integer", "required": True}
        ],
        "responses": {200: {"description": "Holding"}, 404: {"description": "Not found"}},
    }
)
def get_holding(holding_id):
    holding = Holding.query.get_or_404(holding_id)
    return jsonify(holding.to_dict()), 200


@api.route("/holdings", methods=["POST"])
@swag_from(
    {
        "tags": ["Holdings"],
        "summary": "Buy - add a new holding to the portfolio",
        "parameters": [
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "example": "AAPL"},
                        "quantity": {"type": "number", "example": 10},
                        "purchase_price": {"type": "number", "example": 150.25},
                        "purchase_date": {"type": "string", "example": "2026-07-20"},
                    },
                    "required": ["ticker", "quantity", "purchase_price"],
                },
            }
        ],
        "responses": {201: {"description": "Holding created"}},
    }
)
def create_holding():
    data = request.get_json(force=True) or {}

    ticker = data.get("ticker")
    quantity = data.get("quantity")
    purchase_price = data.get("purchase_price")

    if not ticker or quantity is None or purchase_price is None:
        return (
            jsonify({"error": "ticker, quantity and purchase_price are required"}),
            400,
        )

    purchase_date_str = data.get("purchase_date")
    purchase_date = (
        datetime.strptime(purchase_date_str, "%Y-%m-%d").date()
        if purchase_date_str
        else None
    )

    ticker_upper = ticker.upper()
    holding = Holding(
        ticker=ticker_upper,
        quantity=quantity,
        purchase_price=purchase_price,
        **({"purchase_date": purchase_date} if purchase_date else {}),
    )
    db.session.add(holding)

    transaction = Transaction(
        action="buy",
        ticker=ticker_upper,
        quantity=quantity,
        price=purchase_price,
        **({"transaction_date": purchase_date} if purchase_date else {}),
    )
    db.session.add(transaction)
    db.session.commit()

    return jsonify(holding.to_dict()), 201


@api.route("/holdings/<int:holding_id>", methods=["DELETE"])
@swag_from(
    {
        "tags": ["Holdings"],
        "summary": "Sell - remove or reduce a holding from the portfolio",
        "parameters": [
            {"name": "holding_id", "in": "path", "type": "integer", "required": True},
            {
                "name": "quantity",
                "in": "query",
                "type": "number",
                "required": False,
                "description": "Quantity to sell (if not provided, entire holding is sold)"
            }
        ],
        "responses": {204: {"description": "Holding deleted or updated"}, 404: {"description": "Not found"}},
    }
)
def delete_holding(holding_id):
    holding = Holding.query.get_or_404(holding_id)
    quantity_to_sell = request.args.get("quantity", type=float)
    sell_date_str = request.args.get("sell_date")
    sell_date = (
        datetime.strptime(sell_date_str, "%Y-%m-%d").date()
        if sell_date_str
        else None
    )

    if quantity_to_sell:
        transaction = Transaction(
            action="sell",
            ticker=holding.ticker,
            quantity=quantity_to_sell,
            price=holding.purchase_price,
            **({"transaction_date": sell_date} if sell_date else {}),
        )
        db.session.add(transaction)
        holding.quantity -= quantity_to_sell
        if holding.quantity <= 0:
            db.session.delete(holding)
        db.session.commit()
    else:
        transaction = Transaction(
            action="sell",
            ticker=holding.ticker,
            quantity=holding.quantity,
            price=holding.purchase_price,
            **({"transaction_date": sell_date} if sell_date else {}),
        )
        db.session.add(transaction)
        db.session.delete(holding)
        db.session.commit()

    return "", 204


@api.route("/consolidated", methods=["GET"])
@swag_from(
    {
        "tags": ["Portfolio"],
        "summary": "Get consolidated portfolio (grouped by ticker)",
        "responses": {200: {"description": "Consolidated holdings by ticker"}},
    }
)
def get_consolidated():
    from sqlalchemy import func

    consolidated = db.session.query(
        Holding.ticker,
        func.sum(Holding.quantity).label("total_quantity"),
        func.sum(Holding.quantity * Holding.purchase_price).label("weighted_cost"),
    ).group_by(Holding.ticker).all()

    payload = []
    for ticker, total_quantity, weighted_cost in consolidated:
        avg_price = float(weighted_cost / total_quantity) if total_quantity else 0
        payload.append(
            {
                "ticker": ticker,
                "quantity": float(total_quantity),
                "avg_price": avg_price,
            }
        )

    return jsonify(payload), 200


@api.route("/transactions", methods=["GET"])
@swag_from(
    {
        "tags": ["Portfolio"],
        "summary": "Get transaction history",
        "responses": {200: {"description": "List of all transactions"}},
    }
)
def get_transactions():
    query = Transaction.query

    action = request.args.get("action", "", type=str)
    ticker = request.args.get("ticker", "", type=str)
    quantity_value = request.args.get("quantity", type=str)
    year_value = request.args.get("year", "", type=str)
    price_value = request.args.get("price", type=str)
    price_range = request.args.get("price_range", "", type=str)
    date_value = request.args.get("date", "", type=str)

    if action:
        query = query.filter(Transaction.action.like(f"%{action.lower()}%"))

    if ticker:
        query = query.filter(Transaction.ticker.like(f"%{ticker.upper()}%"))

    if quantity_value:
        try:
            quantity_operator, quantity_text = _parse_operator_value(quantity_value)
            quantity_number = float(quantity_text)
            if quantity_operator == "<":
                query = query.filter(Transaction.quantity < quantity_number)
            elif quantity_operator == ">":
                query = query.filter(Transaction.quantity > quantity_number)
            elif quantity_operator == "<=":
                query = query.filter(Transaction.quantity <= quantity_number)
            elif quantity_operator == ">=":
                query = query.filter(Transaction.quantity >= quantity_number)
            else:
                query = query.filter(Transaction.quantity == quantity_number)
        except ValueError:
            pass

    if year_value:
        try:
            year_int = int(year_value)
            query = query.filter(db.func.extract("year", Transaction.transaction_date) == year_int)
        except ValueError:
            pass

    if price_value:
        try:
            price_operator, price_text = _parse_operator_value(price_value)
            price_number = float(price_text)
            if price_operator == "<":
                query = query.filter(Transaction.price < price_number)
            elif price_operator == ">":
                query = query.filter(Transaction.price > price_number)
            elif price_operator == "<=":
                query = query.filter(Transaction.price <= price_number)
            elif price_operator == ">=":
                query = query.filter(Transaction.price >= price_number)
            else:
                query = query.filter(Transaction.price == price_number)
        except ValueError:
            pass

    if date_value:
        try:
            parsed_date = datetime.strptime(date_value, "%Y-%m-%d").date()
            query = query.filter(Transaction.transaction_date == parsed_date)
        except ValueError:
            pass

    if price_range:
        if price_range == "0-50":
            query = query.filter(Transaction.price >= 0, Transaction.price <= 50)
        elif price_range == "50-100":
            query = query.filter(Transaction.price > 50, Transaction.price <= 100)
        elif price_range == "100-500":
            query = query.filter(Transaction.price > 100, Transaction.price <= 500)
        elif price_range == "500-1000":
            query = query.filter(Transaction.price > 500, Transaction.price <= 1000)
        elif price_range == "1000+":
            query = query.filter(Transaction.price > 1000)

    transactions = query.order_by(Transaction.transaction_date.desc()).all()
    return jsonify([t.to_dict() for t in transactions]), 200
