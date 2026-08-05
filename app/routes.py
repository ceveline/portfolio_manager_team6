from datetime import date, datetime, timedelta
import yfinance as yf

from curl_cffi import requests as curl_requests
from flasgger import swag_from
from flask import Flask, Blueprint, jsonify, request, render_template

from app import db, performance, price_backfill
from app.models import User, PriceHistory, Transaction

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


@api.route("/users", methods=["GET"])
def list_users():
    users = User.query.all()

    return jsonify(
        [user.to_dict() for user in users]
    ), 200

@api.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = User.query.get_or_404(user_id)

    return jsonify(user.to_dict()), 200

@api.route("/users", methods=["POST"])
def create_user():

    data = request.get_json(force=True) or {}

    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    account_balance = data.get("account_balance", 0)

    if not first_name or not last_name or not email:
        return jsonify({
            "error": "first_name, last_name and email are required"
        }), 400


    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        return jsonify({
            "error": "Email already exists"
        }), 409


    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        account_balance=account_balance
    )

    db.session.add(user)
    db.session.commit()


    return jsonify(user.to_dict()), 201

@api.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):

    user = User.query.get_or_404(user_id)

    data = request.get_json(force=True) or {}


    user.first_name = data.get(
        "first_name",
        user.first_name
    )

    user.last_name = data.get(
        "last_name",
        user.last_name
    )

    user.email = data.get(
        "email",
        user.email
    )

    user.account_balance = data.get(
        "account_balance",
        user.account_balance
    )


    db.session.commit()

    return jsonify(user.to_dict()), 200

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
        "summary": "Get consolidated holdings (grouped by ticker)",
        "responses": {200: {"description": "Consolidated holdings by ticker"}},
    }
)
def list_holdings():
    tickers = performance.all_tickers()

    result = []
    for ticker in tickers:
        pos = performance.replay_position(ticker)
        if pos["shares_held"] > 0:
            result.append({
                "ticker": ticker,
                "quantity": float(pos["shares_held"]),
                "avg_price": float(pos["avg_cost"]),
            })

    return jsonify(result), 200


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

    # Check if user has sufficient balance
    cost = quantity * purchase_price
    user = User.query.first()  # Get default user
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.account_balance < cost:
        return jsonify({
            "error": f"Insufficient balance. Required: ${cost:.2f}, Available: ${user.account_balance:.2f}"
        }), 400

    transaction = Transaction(
        action="buy",
        ticker=ticker_upper,
        quantity=quantity,
        price=purchase_price,
        **({"transaction_date": purchase_date} if purchase_date else {}),
    )
    db.session.add(transaction)

    # Update user account balance (deduct purchase cost)
    from decimal import Decimal
    user.account_balance -= Decimal(str(cost))

    db.session.commit()

    return jsonify({
        "ticker": ticker_upper,
        "quantity": quantity,
        "purchase_price": purchase_price,
        "purchase_date": purchase_date.isoformat() if purchase_date else date.today().isoformat(),
    }), 201


@api.route("/holdings/sell", methods=["POST"])
@swag_from(
    {
        "tags": ["Holdings"],
        "summary": "Sell - record a sell transaction for a ticker",
        "parameters": [
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "example": "AAPL"},
                        "quantity": {"type": "number", "example": 5},
                        "sell_price": {"type": "number", "example": 175.50},
                        "sell_date": {"type": "string", "example": "2026-07-25"},
                    },
                    "required": ["ticker", "quantity", "sell_price"],
                },
            }
        ],
        "responses": {201: {"description": "Transaction created"}, 400: {"description": "Validation error"}},
    }
)
def sell_holding():
    from decimal import Decimal

    data = request.get_json(force=True) or {}
    ticker = data.get("ticker")
    quantity_to_sell = data.get("quantity")
    sell_price_raw = data.get("sell_price")
    sell_date_str = data.get("sell_date")

    if not ticker or quantity_to_sell is None or sell_price_raw is None:
        return jsonify({"error": "ticker, quantity, and sell_price are required"}), 400

    ticker_upper = ticker.upper()
    sell_price = Decimal(str(round(sell_price_raw, 2)))

    sell_date = (
        datetime.strptime(sell_date_str, "%Y-%m-%d").date()
        if sell_date_str
        else None
    )

    transaction = Transaction(
        action="sell",
        ticker=ticker_upper,
        quantity=quantity_to_sell,
        price=float(sell_price),
        **({"transaction_date": sell_date} if sell_date else {}),
    )
    db.session.add(transaction)

    # Update user account balance (add sale proceeds at market price)
    proceeds = Decimal(str(quantity_to_sell)) * sell_price
    user = User.query.first()
    if user:
        user.account_balance += proceeds

    db.session.commit()

    return jsonify({
        "ticker": ticker_upper,
        "quantity": quantity_to_sell,
        "sell_price": float(sell_price),
        "sell_date": sell_date.isoformat() if sell_date else date.today().isoformat(),
    }), 201


@api.route("/consolidated", methods=["GET"])
@swag_from(
    {
        "tags": ["Portfolio"],
        "summary": "Get consolidated portfolio (grouped by ticker)",
        "responses": {200: {"description": "Consolidated holdings by ticker"}},
    }
)
def get_consolidated():
    # Get all tickers from transaction history
    tickers = performance.all_tickers()

    result = []
    for ticker in tickers:
        pos = performance.replay_position(ticker)
        if pos["shares_held"] > 0:
            result.append({
                "ticker": ticker,
                "quantity": float(pos["shares_held"]),
                "avg_price": float(pos["avg_cost"]),
            })

    return jsonify(result), 200


# Alias /api/portfolio to the consolidated endpoint (used by tests and UI)
@api.route("/portfolio", methods=["GET"])
def get_portfolio():
    return get_consolidated()


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


@api.route("/win-rate", methods=["GET"])
@swag_from(
    {
        "tags": ["Portfolio"],
        "summary": "Calculate win rate: percentage of sell transactions that were profitable",
        "responses": {200: {"description": "Win rate statistics"}},
    }
)
def get_win_rate():
    win_rate = performance.calculate_win_rate()
    return jsonify(win_rate), 200


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
