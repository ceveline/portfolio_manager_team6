"""Backfill PriceHistory with historical daily closes from yfinance.

Per team decision: yfinance is for PAST data only. Live/current prices
always come from the AWS cached API (see routes._fetch_current_price). This module never touches
"today's" price, only history.
"""

from datetime import date, timedelta

from curl_cffi import requests as curl_requests
import yfinance as yf

from app import db
from app.models import PriceHistory

# Same fix as app/routes.py: Yahoo blocks plain requests-library traffic
# and yfinance raises a JSONDecodeError / "possibly delisted" for real,
# valid tickers as a result. Impersonating a browser TLS fingerprint
# fixes it.
_yf_session = curl_requests.Session(impersonate="chrome")


def backfill_ticker(ticker, start_date=None, end_date=None):
    """Pull daily closes for one ticker from yfinance and upsert them
    into price_history. Returns a small summary dict; never raises, so
    one bad ticker doesn't abort a multi-ticker backfill_all() call.
    """
    end_date = end_date or date.today()
    start_date = start_date or end_date - timedelta(days=180)

    try:
        hist = yf.download(
            ticker,
            start=start_date.isoformat(),
            # yfinance's `end` is exclusive, so add a day to include end_date
            end=(end_date + timedelta(days=1)).isoformat(),
            progress=False,
            session=_yf_session,
        )
    except Exception as exc:
        return {"ticker": ticker, "inserted": 0, "updated": 0, "error": str(exc)}

    if hist.empty:
        return {
            "ticker": ticker,
            "inserted": 0,
            "updated": 0,
            "error": "no data returned for this ticker/date range",
        }

    inserted, updated = 0, 0
    for idx, row in hist.iterrows():
        price_date = idx.date()
        close_price = float(row["Close"])

        existing = PriceHistory.query.filter_by(
            ticker=ticker, price_date=price_date
        ).first()
        if existing:
            existing.close_price = close_price
            updated += 1
        else:
            db.session.add(
                PriceHistory(
                    ticker=ticker, price_date=price_date, close_price=close_price
                )
            )
            inserted += 1

    db.session.commit()
    return {"ticker": ticker, "inserted": inserted, "updated": updated}


def backfill_all(tickers, start_date=None, end_date=None):
    """Backfill a list of tickers, e.g. every ticker currently in
    Transaction history (see performance.all_tickers()).
    """
    return [backfill_ticker(t, start_date, end_date) for t in tickers]
