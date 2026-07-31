"""Portfolio performance calculations.

Combines the Transaction audit trail (what was bought/sold and when)
with the PriceHistory table (what a ticker was worth on a given day) to
produce cost basis, realized/unrealized P&L, and a day-by-day portfolio
value series for charting.

Cost basis uses the average-cost method: every buy updates a running
average cost per share for that ticker; every sell realizes P&L against
that average without changing it.
"""

from datetime import timedelta

from sqlalchemy import func

from app import db
from app.models import PriceHistory, Transaction


def all_tickers():
    """Every ticker that has ever appeared in a transaction."""
    rows = db.session.query(Transaction.ticker).distinct().all()
    return sorted(r[0] for r in rows)


def _ticker_transactions(ticker):
    return (
        Transaction.query.filter(Transaction.ticker == ticker)
        .order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
        .all()
    )


def replay_position(ticker):
    """Replay a ticker's buy/sell history to get shares currently held,
    their average cost, and realized P&L from any sells.
    """
    shares = 0.0
    avg_cost = 0.0
    realized_pnl = 0.0
    total_invested = 0.0
    total_divested = 0.0

    for tx in _ticker_transactions(ticker):
        if tx.action == "buy":
            total_invested += tx.price * tx.quantity
            new_shares = shares + tx.quantity
            avg_cost = (
                (avg_cost * shares + tx.price * tx.quantity) / new_shares
                if new_shares
                else 0.0
            )
            shares = new_shares
        elif tx.action == "sell":
            sell_qty = min(tx.quantity, shares)
            realized_pnl += (tx.price - avg_cost) * sell_qty
            total_divested += tx.price * sell_qty
            shares -= sell_qty

    return {
        "ticker": ticker,
        "shares_held": round(shares, 4),
        "avg_cost": round(avg_cost, 4),
        "realized_pnl": round(realized_pnl, 2),
        "total_invested": round(total_invested, 2),
        "total_divested": round(total_divested, 2),
    }


def shares_held_as_of(ticker, as_of_date):
    """Net shares held for a ticker at end-of-day on as_of_date."""
    buys = (
        db.session.query(func.coalesce(func.sum(Transaction.quantity), 0))
        .filter(
            Transaction.ticker == ticker,
            Transaction.action == "buy",
            Transaction.transaction_date <= as_of_date,
        )
        .scalar()
    )
    sells = (
        db.session.query(func.coalesce(func.sum(Transaction.quantity), 0))
        .filter(
            Transaction.ticker == ticker,
            Transaction.action == "sell",
            Transaction.transaction_date <= as_of_date,
        )
        .scalar()
    )
    return float(buys) - float(sells)


def price_on_or_before(ticker, as_of_date):
    """Latest known close for ticker on or before as_of_date (forward
    fills over weekends/holidays that have no price_history row).
    """
    row = (
        PriceHistory.query.filter(
            PriceHistory.ticker == ticker, PriceHistory.price_date <= as_of_date
        )
        .order_by(PriceHistory.price_date.desc())
        .first()
    )
    return row.close_price if row else None


def portfolio_value_series(start_date, end_date, tickers=None):
    """Portfolio value series with batch data loading for performance.
    Loads all transactions and prices once, then calculates in-memory.
    """
    tickers = tickers or all_tickers()
    if not tickers:
        return []

    # Batch load all data upfront
    all_transactions = Transaction.query.filter(
        Transaction.ticker.in_(tickers),
        Transaction.transaction_date <= end_date
    ).all()

    all_prices = PriceHistory.query.filter(
        PriceHistory.ticker.in_(tickers),
        PriceHistory.price_date <= end_date
    ).all()

    # Build in-memory indexes for fast lookups
    tx_by_ticker = {}
    for tx in all_transactions:
        if tx.ticker not in tx_by_ticker:
            tx_by_ticker[tx.ticker] = []
        tx_by_ticker[tx.ticker].append(tx)

    # Sort transactions by date for replay
    for ticker_txs in tx_by_ticker.values():
        ticker_txs.sort(key=lambda t: (t.transaction_date, t.id))

    # Build price index: {ticker: {date: price}}
    price_by_date = {}
    for price in all_prices:
        if price.ticker not in price_by_date:
            price_by_date[price.ticker] = {}
        price_by_date[price.ticker][price.price_date] = price.close_price

    # Determine sampling interval
    date_span = (end_date - start_date).days
    if date_span <= 30:
        step = timedelta(days=1)
    elif date_span <= 180:
        step = timedelta(days=1)
    elif date_span <= 365:
        step = timedelta(weeks=1)
    elif date_span <= 1825:
        step = timedelta(days=30)
    else:
        step = timedelta(days=30)

    # Calculate portfolio value at each sample point
    series = []
    current = start_date
    while current <= end_date:
        total = 0.0
        for ticker in tickers:
            # Replay transactions up to current date
            shares = 0.0
            for tx in tx_by_ticker.get(ticker, []):
                if tx.transaction_date > current:
                    break
                if tx.action == "buy":
                    shares += tx.quantity
                elif tx.action == "sell":
                    shares -= tx.quantity

            if shares <= 0:
                continue

            # Find latest price on or before current date
            prices = price_by_date.get(ticker, {})
            price = None
            for check_date in range((current - start_date).days, -1, -1):
                check = start_date + timedelta(days=check_date)
                if check in prices:
                    price = prices[check]
                    break

            if price is not None:
                total += shares * price

        series.append({"date": current.isoformat(), "value": round(total, 2)})
        current += step

    # Always include end date
    if series and series[-1]["date"] != end_date.isoformat():
        total = 0.0
        for ticker in tickers:
            shares = 0.0
            for tx in tx_by_ticker.get(ticker, []):
                if tx.transaction_date > end_date:
                    break
                if tx.action == "buy":
                    shares += tx.quantity
                elif tx.action == "sell":
                    shares -= tx.quantity

            if shares <= 0:
                continue

            prices = price_by_date.get(ticker, {})
            price = None
            for check_date in range((end_date - start_date).days, -1, -1):
                check = start_date + timedelta(days=check_date)
                if check in prices:
                    price = prices[check]
                    break

            if price is not None:
                total += shares * price

        series.append({"date": end_date.isoformat(), "value": round(total, 2)})

    return series


def calculate_win_rate():
    """Calculate win rate: percentage of sell transactions that were profitable.

    For each sell, calculate realized P&L based on average cost of buys before it.
    Win rate = (number of profitable sells) / (total sells) * 100
    """
    all_transactions = Transaction.query.order_by(
        Transaction.transaction_date.asc(), Transaction.id.asc()
    ).all()

    if not all_transactions:
        return {"win_rate_pct": 0.0, "winning_trades": 0, "total_trades": 0}

    # Track average cost per ticker
    avg_costs = {}
    winning_trades = 0
    total_sells = 0

    for tx in all_transactions:
        if tx.action == "buy":
            # Update average cost for this ticker
            if tx.ticker not in avg_costs:
                avg_costs[tx.ticker] = 0.0

            current_shares = sum(t.quantity for t in all_transactions
                               if t.ticker == tx.ticker
                               and t.action == "buy"
                               and (t.transaction_date < tx.transaction_date or
                                    (t.transaction_date == tx.transaction_date and t.id < tx.id)))
            new_shares = current_shares + tx.quantity
            avg_costs[tx.ticker] = (
                (avg_costs[tx.ticker] * current_shares + tx.price * tx.quantity) / new_shares
                if new_shares > 0 else tx.price
            )
        elif tx.action == "sell":
            total_sells += 1
            avg_cost = avg_costs.get(tx.ticker, 0.0)
            pnl = (tx.price - avg_cost) * tx.quantity
            if pnl > 0:
                winning_trades += 1

    win_rate_pct = (winning_trades / total_sells * 100) if total_sells > 0 else 0.0

    return {
        "win_rate_pct": round(win_rate_pct, 1),
        "winning_trades": winning_trades,
        "total_trades": total_sells
    }


def portfolio_summary(current_prices):
    """current_prices: {ticker: live_price_or_None}. Returns per-ticker
    and total cost basis, market value, and realized/unrealized P&L.
    Uses actual holdings from database as source of truth.
    """
    from app.models import Holding
    from sqlalchemy import func

    positions = []
    total_market_value = 0.0
    total_cost_basis = 0.0
    total_realized_pnl = 0.0

    # Get consolidated holdings grouped by ticker
    consolidated = db.session.query(
        Holding.ticker,
        func.sum(Holding.quantity).label("total_quantity"),
        func.avg(Holding.purchase_price).label("avg_price"),
    ).group_by(Holding.ticker).all()

    for ticker, total_quantity, avg_price in consolidated:
        if total_quantity <= 0:
            continue

        # Get realized P&L from transactions
        pos = replay_position(ticker)
        realized_pnl = pos["realized_pnl"]
        total_realized_pnl += realized_pnl

        current_price = current_prices.get(ticker)
        cost_basis_value = round(total_quantity * avg_price, 2)
        market_value = (
            round(total_quantity * current_price, 2)
            if current_price is not None
            else None
        )

        positions.append(
            {
                "ticker": ticker,
                "shares_held": total_quantity,
                "avg_cost": round(avg_price, 2),
                "current_price": current_price,
                "cost_basis": cost_basis_value,
                "market_value": market_value,
                "unrealized_pnl": (
                    round(market_value - cost_basis_value, 2)
                    if market_value is not None
                    else None
                ),
                "realized_pnl": realized_pnl,
            }
        )

        if market_value is not None:
            total_market_value += market_value
        total_cost_basis += cost_basis_value

    total_return_pct = 0.0
    if total_cost_basis > 0:
        total_return_pct = round(
            ((total_market_value + total_realized_pnl - total_cost_basis) / total_cost_basis) * 100, 2
        )

    return {
        "positions": positions,
        "total_market_value": round(total_market_value, 2),
        "total_cost_basis": round(total_cost_basis, 2),
        "total_unrealized_pnl": round(total_market_value - total_cost_basis, 2),
        "total_realized_pnl": round(total_realized_pnl, 2),
        "total_return_pct": total_return_pct,
    }
