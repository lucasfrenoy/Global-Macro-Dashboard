# Global Macro Dashboard

A live market monitor built with Streamlit, tracking Indices, Stocks, Currencies, Bonds and Commodities in one place.

## Features
- Sidebar navigation across five asset classes
- Live prices and daily percentage change for a dozen tickers per section
- Click any tile to open an interactive, zoomable chart with a 1M to Max lookback
- A currency cross matrix showing how each major currency moved against every other one today

## Tech stack
Python, Streamlit, yfinance, pandas, Altair, managed with [uv](https://docs.astral.sh/uv/).

## Running locally
```bash
uv sync
uv run streamlit run app.py
```

## Live demo
[Add your Streamlit Community Cloud link here once deployed]
