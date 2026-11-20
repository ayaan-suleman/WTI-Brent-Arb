"""Download free, public daily prices for Brent and WTI.

Spot prices come from FRED (St. Louis Fed), which republishes the US EIA
daily spot series. No API key is needed.
    DCOILBRENTEU  Europe Brent spot, FOB (USD/bbl)
    DCOILWTICO    WTI spot, Cushing, Oklahoma (USD/bbl)

Front-month futures come from Yahoo Finance via the yfinance package.
    BZ=F  ICE Brent front month
    CL=F  NYMEX WTI front month
Continuous front-month series jump when the contract rolls; see README.
"""

import io
import urllib.request

import pandas as pd

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}"

SPOT_SERIES = {
    "brent_spot": "DCOILBRENTEU",
    "wti_spot": "DCOILWTICO",
}

FUTURES_SERIES = {
    "brent_fut": "BZ=F",
    "wti_fut": "CL=F",
}


def fetch_fred(series_name, code):
    with urllib.request.urlopen(FRED_URL.format(code=code), timeout=30) as resp:
        raw = pd.read_csv(io.StringIO(resp.read().decode()))
    raw.columns = ["date", "price"]
    # FRED marks days with no assessment as "." - those are not prices.
    raw["price"] = pd.to_numeric(raw["price"], errors="coerce")
    raw = raw.dropna(subset=["price"])
    raw["series"] = series_name
    raw["source"] = f"FRED:{code}"
    return raw


def fetch_yahoo(series_name, ticker, start="2015-01-01"):
    import yfinance as yf  # imported here so spot-only runs don't need it

    hist = yf.download(ticker, start=start, progress=False, auto_adjust=False)
    if hist.empty:
        raise RuntimeError(f"No data returned for {ticker}")
    close = hist["Close"]
    if isinstance(close, pd.DataFrame):  # newer yfinance returns one column per ticker
        close = close.iloc[:, 0]
    out = close.dropna().reset_index()
    out.columns = ["date", "price"]
    out["series"] = series_name
    out["source"] = f"yahoo:{ticker}"
    return out


def fetch_all(include_futures=True):
    frames = [fetch_fred(name, code) for name, code in SPOT_SERIES.items()]
    if include_futures:
        frames += [fetch_yahoo(name, t) for name, t in FUTURES_SERIES.items()]
    return pd.concat(frames, ignore_index=True)
