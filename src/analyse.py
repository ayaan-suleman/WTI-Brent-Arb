"""Align Brent and WTI prices, drop stale legs, and flag unusual spreads.

The core problem: Brent and WTI do not print on the same days. UK and US
markets close on different holidays, and a feed can simply miss a day.
If you forward-fill the missing leg, the spread on that day compares a
fresh price with an old one. That looks like a real move but is not.

So for every pair, each leg must have printed within MAX_STALE_DAYS of the
date. If either leg is stale, that day is dropped for that pair.
"""

import pandas as pd

# How old (in calendar days) a leg's last print may be before it counts as
# stale. 0 means both legs must have printed on that exact date.
MAX_STALE_DAYS = 0

# Rolling window for the "recent range" a spread is compared against.
WINDOW = 60

# A spread is flagged when it sits this many standard deviations away
# from its own rolling mean.
Z_THRESHOLD = 2.0

PAIRS = {
    "spot": ("brent_spot", "wti_spot"),
    "futures": ("brent_fut", "wti_fut"),
}


def to_wide(long_df):
    """One row per date, one column per series. Missing days stay NaN."""
    return long_df.pivot(index="date", columns="series", values="price").sort_index()


def last_print_age(wide, col):
    """For each date, how many days since this series last actually printed."""
    printed = wide[col].notna()
    last_date = pd.Series(wide.index.where(printed), index=wide.index).ffill()
    return (wide.index - last_date).dt.days


def build_spread(wide, brent_col, wti_col, clean=True):
    """Brent minus WTI, in USD/bbl.

    clean=True  -> drop any day where either leg is stale.
    clean=False -> the naive version: forward-fill both legs and subtract.
    """
    filled = wide[[brent_col, wti_col]].ffill()
    spread = filled[brent_col] - filled[wti_col]

    if clean:
        fresh = (last_print_age(wide, brent_col) <= MAX_STALE_DAYS) & (
            last_print_age(wide, wti_col) <= MAX_STALE_DAYS
        )
        spread = spread[fresh]

    return spread.dropna()


def add_signals(spread, window=WINDOW, z_threshold=Z_THRESHOLD):
    """Compare each day's spread with its own recent range."""
    df = spread.to_frame("spread")
    roll = df["spread"].rolling(window, min_periods=window)
    df["mean"] = roll.mean()
    df["std"] = roll.std()
    df["z"] = (df["spread"] - df["mean"]) / df["std"]
    df["flag"] = df["z"].abs() >= z_threshold
    return df


def run(long_df):
    """Build clean and naive versions of every available pair.

    Returns a dict: pair name -> {'clean': DataFrame, 'naive': DataFrame}.
    """
    wide = to_wide(long_df)
    results = {}
    for name, (b, w) in PAIRS.items():
        if b not in wide or w not in wide:
            continue
        results[name] = {
            "clean": add_signals(build_spread(wide, b, w, clean=True)),
            "naive": add_signals(build_spread(wide, b, w, clean=False)),
        }
    return results


def latest_report(results, top_n=5):
    """Most recent flagged days per pair, from the clean series only."""
    rows = []
    for name, res in results.items():
        flagged = res["clean"][res["clean"]["flag"]].tail(top_n)
        for date, r in flagged.iterrows():
            rows.append(
                {
                    "pair": f"Brent-WTI {name}",
                    "date": date.date(),
                    "spread_usd_bbl": round(r["spread"], 2),
                    "rolling_mean": round(r["mean"], 2),
                    "z_score": round(r["z"], 2),
                }
            )
    return pd.DataFrame(rows)
