# Brent–WTI Spread Monitor

A small Python and SQL tool that tracks the transatlantic crude spread, Brent minus WTI, in both spot and front-month futures, and flags days when the spread moves unusually far from its recent range.

This is a first version. It covers crude only; refined products are next.

## Why this spread

Brent prices crude delivered into Europe; WTI prices crude at Cushing, Oklahoma. The gap between them roughly tells you whether US barrels can be shipped across the Atlantic at a profit once freight is paid. When the spread widens well beyond freight, US exports tend to pick up; when it narrows, the arbitrage closes.

## What it does

1. **Downloads** daily prices from free public sources:
   - Spot: Europe Brent FOB and WTI Cushing, from FRED (which republishes the US EIA series).
   - Futures: ICE Brent and NYMEX WTI front month, from Yahoo Finance.
   - Additional: Onyx Flux data currently used for manual checks
2. **Stores** every raw observation in a SQLite database (`data/prices.db`), one row per date and series, with no gaps filled in.
3. **Aligns** the two legs of each pair and **drops any day where one leg did not actually print**.
4. **Flags** days where the spread sits two or more standard deviations from its 60-day rolling mean.
5. **Outputs** a CSV of the latest flagged days and a chart.

## The main problem: stale legs

Brent and WTI don't always print on the same day. UK and US markets have different holidays, and data feeds occasionally miss a day or lag.

The obvious approach is to forward-fill the missing price and carry on. But then on that day the spread compares today's Brent with yesterday's WTI (or worse, last week's). Any move in the fresh leg shows up as a jump in the spread that never happened.

So the model keeps two versions of every spread:

- **Naive:** forward-fill both legs and subtract.
- **Clean:** only keep days where both legs printed (`MAX_STALE_DAYS` in `src/analyse.py`).

Each run prints how many signals each version produces. The difference is the number of false signals that came purely from misaligned data.

## How to run it

```bash
pip install -r requirements.txt
python run.py               # download data, store it, analyse
python run.py --no-fetch    # re-analyse what is already stored
python run.py --spot-only   # spot prices only, no yfinance needed
python -m pytest            # run the tests
```

Results go to `output/latest_signals.csv` and `output/spreads.png`.

## Project layout

```
run.py              entry point
src/fetch.py        downloads prices from FRED and Yahoo Finance
src/db.py           SQLite schema, save and load
src/analyse.py      alignment, stale-leg filter, rolling z-score signals
tests/              tests on small hand-made series
```

## Settings

All in `src/analyse.py`:

| Setting | Default | Meaning |
|---|---|---|
| `MAX_STALE_DAYS` | 0 | how old a leg's last print can be before the day is dropped |
| `WINDOW` | 60 | trading days in the rolling "recent range" |
| `Z_THRESHOLD` | 2.0 | standard deviations from the rolling mean needed to flag |

## Limitations

- **Daily data only.** Brent and WTI settle at different times of day (London afternoon vs New York afternoon), so even "same-day" prices are a few hours apart. Intraday data would fix this but isn't freely available.
- **Front-month futures roll.** The continuous Yahoo series switches contract each month, which can create a jump in the price that is not a market move. Brent and WTI also roll on different dates.
- **Public spot series are not the trade benchmarks.** The EIA/FRED Brent spot series is not the same as the price-reporting-agency assessments that physical trades are priced against.
- **The z-score is a simple measure.** It assumes the spread behaves roughly normally around its recent mean, which doesn't hold in a crisis.
- **No freight as of yet.** A wide spread only matters if it beats the cost of shipping. Adding a freight estimate is the next step.

## Next steps

- Add a transatlantic freight estimate so the flag means "arbitrage likely open", not just "spread unusual".
- Handle the futures roll properly.
- Extend to refined products (e.g. ULSD, Jet A-1, gasoil, gasoline) across regions.
