from datetime import date, datetime, timedelta
import yfinance as yf

from curl_cffi import requests as curl_requests
from flasgger import swag_from
from flask import Flask, Blueprint, jsonify, request, render_template

from app import db, performance, price_backfill
from app.models import Holding, PriceHistory, Transaction

api = Blueprint("api", __name__, url_prefix="/api")

# Yahoo Finance blocks plain requests-library traffic from most cloud/CI
# IPs (returns empty body -> yfinance raises "Expecting value: line 1
# column 1 (char 0)" / "possibly delisted"). Giving yfinance a session
# that impersonates a real browser's TLS fingerprint fixes this - it's
# not about the ticker being invalid, real tickers get the same error.
app = Flask(__name__)
_yf_session = curl_requests.Session(impersonate="chrome")

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


def _fetch_current_price(ticker):
    """Fetch current price using yfinance with curl_cffi session to avoid
    rate-limiting. The session impersonates a browser's TLS fingerprint so
    Yahoo Finance won't block cloud/CI IPs. Returns float or None if fetch fails.
    """
    ticker_upper = ticker.upper()

    try:
        stock = yf.Ticker(ticker_upper, session=_yf_session)
        hist = stock.history(period="1d")

        if not hist.empty:
            return float(hist["Close"].iloc[-1])

    except Exception as e:
        print(f"Failed to fetch {ticker_upper}: {e}")

    return None


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
    price = _fetch_current_price(ticker)
    if price is None:
        return jsonify({"error": f"Could not fetch price for {ticker}"}), 400
    return jsonify({"ticker": ticker.upper(), "price": price}), 200


@api.route("/ticker/<ticker>", methods=["GET"])
@swag_from(
    {
        "tags": ["Stock Data"],
        "summary": "Get detailed ticker information from Yahoo Finance",
        "parameters": [
            {"name": "ticker", "in": "path", "type": "string", "required": True}
        ],
        "responses": {
            200: {"description": "Detailed ticker information"},
            400: {"description": "Invalid ticker or unable to fetch info"}
        },
    }
)
def get_ticker_info(ticker):
    ticker_upper = ticker.upper()

    try:
        stock = yf.Ticker(ticker_upper, session=_yf_session)
        info = stock.info

        if not info:
            return jsonify({"error": f"No data found for {ticker_upper}"}), 400

        return jsonify({
            "ticker": ticker_upper,
            "name": info.get("longName", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "currentPrice": info.get("currentPrice", None),
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh", None),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow", None),
            "marketCap": info.get("marketCap", None),
            "peRatio": info.get("trailingPE", None),
            "dividendYield": info.get("dividendYield", None),
            "beta": info.get("beta", None),
            "avgVolume": info.get("averageVolume", None),
            "website": info.get("website", ""),
        }), 200
    except Exception as e:
        print(f"Failed to get ticker info for {ticker_upper}: {e}")
        return jsonify({"error": f"Could not fetch info for {ticker_upper}"}), 400


@api.route("/holdings", methods=["GET"])
@swag_from(
    {
        "tags": ["Holdings"],
        "summary": "List all holdings",
        "responses": {200: {"description": "List of holdings"}},
    }
)
def list_holdings():
    print("Holdings requested at", datetime.now())
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
        func.avg(Holding.purchase_price).label("avg_price"),
    ).group_by(Holding.ticker).all()

    return jsonify([
        {
            "ticker": row[0],
            "quantity": float(row[1]),
            "avg_price": float(row[2]) if row[2] else 0,
        }
        for row in consolidated
    ]), 200


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


@api.route("/price-history", methods=["GET"])
@swag_from(
    {
        "tags": ["Stock Data"],
        "summary": "Get stored historical daily closes (backfilled from yfinance via /price-history/backfill)",
        "parameters": [
            {
                "name": "ticker",
                "in": "query",
                "type": "string",
                "required": False,
                "description": "Filter to one ticker; omit for every ticker with stored history",
            },
            {"name": "start", "in": "query", "type": "string", "required": False, "example": "2026-01-01"},
            {"name": "end", "in": "query", "type": "string", "required": False, "example": "2026-07-23"},
        ],
        "responses": {200: {"description": "List of {ticker, date, close_price} rows, most recent first"}},
    }
)
def get_price_history():
    query = PriceHistory.query

    ticker = request.args.get("ticker")
    if ticker:
        query = query.filter(PriceHistory.ticker == ticker.upper())

    start_str = request.args.get("start")
    if start_str:
        query = query.filter(
            PriceHistory.price_date >= datetime.strptime(start_str, "%Y-%m-%d").date()
        )

    end_str = request.args.get("end")
    if end_str:
        query = query.filter(
            PriceHistory.price_date <= datetime.strptime(end_str, "%Y-%m-%d").date()
        )

    rows = query.order_by(PriceHistory.ticker.asc(), PriceHistory.price_date.desc()).all()
    return jsonify([r.to_dict() for r in rows]), 200


@api.route("/price-history/backfill", methods=["POST"])
@swag_from(
    {
        "tags": ["Stock Data"],
        "summary": "Backfill historical daily prices from yfinance (past data only - not live prices)",
        "parameters": [
            {
                "name": "body",
                "in": "body",
                "required": False,
                "schema": {
                    "type": "object",
                    "properties": {
                        "tickers": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Defaults to every ticker with a transaction",
                        },
                        "start": {"type": "string", "example": "2026-01-01"},
                        "end": {"type": "string", "example": "2026-07-23"},
                    },
                },
            }
        ],
        "responses": {
            200: {"description": "Backfill result per ticker"},
            400: {"description": "No tickers to backfill"},
        },
    }
)
def backfill_price_history():
    data = request.get_json(silent=True) or {}

    tickers = data.get("tickers") or performance.all_tickers()
    if not tickers:
        return jsonify({"error": "no tickers to backfill (no transactions yet)"}), 400

    start_date = (
        datetime.strptime(data["start"], "%Y-%m-%d").date() if data.get("start") else None
    )
    end_date = (
        datetime.strptime(data["end"], "%Y-%m-%d").date() if data.get("end") else None
    )

    result = price_backfill.backfill_all(tickers, start_date, end_date)
    return jsonify(result), 200


@api.route("/summary", methods=["GET"])
@swag_from(
    {
        "tags": ["Portfolio"],
        "summary": "Portfolio summary: cost basis, market value, realized/unrealized P&L per ticker and total",
        "responses": {200: {"description": "Portfolio summary"}},
    }
)
def get_summary():
    tickers = performance.all_tickers()
    current_prices = {t: _fetch_current_price(t) for t in tickers}
    return jsonify(performance.portfolio_summary(current_prices)), 200


@api.route("/performance", methods=["GET"])
@swag_from(
    {
        "tags": ["Portfolio"],
        "summary": "Daily portfolio value over time, for charting performance",
        "parameters": [
            {
                "name": "start",
                "in": "query",
                "type": "string",
                "required": False,
                "description": "YYYY-MM-DD, defaults to 90 days before end",
            },
            {
                "name": "end",
                "in": "query",
                "type": "string",
                "required": False,
                "description": "YYYY-MM-DD, defaults to today",
            },
        ],
        "responses": {
            200: {"description": "Time series of {date, value}"},
            400: {"description": "Invalid date range"},
        },
    }
)
def get_performance():
    end_str = request.args.get("end")
    start_str = request.args.get("start")

    end_date = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else date.today()
    start_date = (
        datetime.strptime(start_str, "%Y-%m-%d").date()
        if start_str
        else end_date - timedelta(days=90)
    )

    if start_date > end_date:
        return jsonify({"error": "start date must be before end date"}), 400

    series = performance.portfolio_value_series(start_date, end_date)
    return jsonify(series), 200
