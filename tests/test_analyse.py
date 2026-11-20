"""Tests use small made-up price series so the logic can be checked by hand.

They are synthetic on purpose: the point is to prove the alignment rules,
not to say anything about the market.
"""

import pandas as pd

from src import analyse


def make_long(rows):
    df = pd.DataFrame(rows, columns=["date", "series", "price"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_stale_leg_is_dropped_in_clean_but_kept_in_naive():
    # WTI does not print on the 3rd (think: US holiday). Brent jumps that day.
    rows = [
        ("2026-01-01", "brent_spot", 80.0), ("2026-01-01", "wti_spot", 76.0),
        ("2026-01-02", "brent_spot", 80.5), ("2026-01-02", "wti_spot", 76.4),
        ("2026-01-03", "brent_spot", 83.0),
        ("2026-01-04", "brent_spot", 81.0), ("2026-01-04", "wti_spot", 77.0),
    ]
    wide = analyse.to_wide(make_long(rows))

    naive = analyse.build_spread(wide, "brent_spot", "wti_spot", clean=False)
    clean = analyse.build_spread(wide, "brent_spot", "wti_spot", clean=True)

    # Naive compares a fresh Brent with a day-old WTI: a fake 6.60 spread.
    assert round(naive[pd.Timestamp("2026-01-03")], 2) == 6.60
    # Clean simply has no value for that day.
    assert pd.Timestamp("2026-01-03") not in clean.index
    assert len(clean) == 3


def test_last_print_age_counts_days_since_real_print():
    rows = [
        ("2026-01-01", "brent_spot", 80.0), ("2026-01-01", "wti_spot", 76.0),
        ("2026-01-02", "brent_spot", 80.5),
        ("2026-01-03", "brent_spot", 80.7),
    ]
    wide = analyse.to_wide(make_long(rows))
    age = analyse.last_print_age(wide, "wti_spot")
    assert list(age) == [0, 1, 2]


def test_flag_fires_on_outlier_only():
    dates = pd.date_range("2026-01-01", periods=80, freq="D")
    values = [4.0 + 0.1 * ((i % 5) - 2) for i in range(80)]
    values[-1] = 9.0  # one obvious blowout at the end
    spread = pd.Series(values, index=dates)

    sig = analyse.add_signals(spread, window=60, z_threshold=2.0)
    assert sig["flag"].iloc[-1]
    assert sig["flag"].iloc[:-1].sum() == 0
