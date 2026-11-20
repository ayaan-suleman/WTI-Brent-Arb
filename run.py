"""Entry point.

    python run.py              # download fresh data, store it, analyse
    python run.py --no-fetch   # analyse whatever is already in data/prices.db
    python run.py --spot-only  # skip futures (no yfinance needed)
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src import analyse, db, fetch

OUT = Path(__file__).resolve().parent / "output"


def plot(results, path):
    fig, axes = plt.subplots(len(results), 1, figsize=(10, 4 * len(results)), squeeze=False)
    for ax, (name, res) in zip(axes[:, 0], results.items()):
        df = res["clean"].dropna(subset=["mean"]).tail(500)
        ax.plot(df.index, df["spread"], lw=1, label="Brent - WTI")
        ax.plot(df.index, df["mean"], lw=1, ls="--", label=f"{analyse.WINDOW}-day mean")
        band = analyse.Z_THRESHOLD * df["std"]
        ax.fill_between(df.index, df["mean"] - band, df["mean"] + band, alpha=0.15,
                        label=f"±{analyse.Z_THRESHOLD:g} std")
        flagged = df[df["flag"]]
        ax.scatter(flagged.index, flagged["spread"], s=12, color="red", zorder=3, label="flagged")
        ax.set_title(f"Brent - WTI {name} spread (USD/bbl)")
        ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=120)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--no-fetch", action="store_true")
    p.add_argument("--spot-only", action="store_true")
    args = p.parse_args()

    conn = db.connect()
    if not args.no_fetch:
        prices = fetch.fetch_all(include_futures=not args.spot_only)
        db.save_prices(conn, prices)
        print(f"Stored {len(prices):,} price rows in {db.DB_PATH}")

    results = analyse.run(db.load_prices(conn))
    if not results:
        raise SystemExit("No complete Brent/WTI pair in the database yet.")

    print("\nSignals: naive (forward-filled) vs clean (stale legs dropped)")
    for name, res in results.items():
        naive = int(res["naive"]["flag"].sum())
        clean = int(res["clean"]["flag"].sum())
        print(f"  {name:8s} naive {naive:5d}   clean {clean:5d}   removed {naive - clean:5d}")

    OUT.mkdir(exist_ok=True)
    report = analyse.latest_report(results)
    report.to_csv(OUT / "latest_signals.csv", index=False)
    plot(results, OUT / "spreads.png")
    print("\nMost recent flagged days:")
    print(report.to_string(index=False) if not report.empty else "  none")
    print(f"\nWrote {OUT / 'latest_signals.csv'} and {OUT / 'spreads.png'}")


if __name__ == "__main__":
    main()
