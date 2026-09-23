import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

st.set_page_config(page_title="Global Macro Dashboard", layout="wide")

CATEGORIES = {
    "Indices": {
        "^GSPC": "S&P 500", "^DJI": "Dow Jones", "^IXIC": "Nasdaq", "^RUT": "Russell 2000",
        "^FTSE": "FTSE 100", "^GDAXI": "DAX", "^FCHI": "CAC 40", "^N225": "Nikkei 225",
        "^HSI": "Hang Seng", "^STOXX50E": "Euro Stoxx 50", "^BVSP": "Bovespa", "^VIX": "VIX",
    },
    "Stocks": {
        "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet", "AMZN": "Amazon",
        "NVDA": "Nvidia", "META": "Meta", "TSLA": "Tesla", "JPM": "JPMorgan",
        "XOM": "Exxon Mobil", "JNJ": "Johnson & Johnson", "V": "Visa", "WMT": "Walmart",
    },
    "Currencies": {
        "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY", "USDCHF=X": "USD/CHF",
        "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "NZDUSD=X": "NZD/USD", "USDCNY=X": "USD/CNY",
        "EURGBP=X": "EUR/GBP", "EURJPY=X": "EUR/JPY", "DX-Y.NYB": "Dollar Index", "USDMXN=X": "USD/MXN",
    },
    "Bonds": {
        "^TNX": "US 10Y Yield", "^TYX": "US 30Y Yield", "^FVX": "US 5Y Yield", "^IRX": "US 13W Yield",
        "TLT": "20Y+ Treasury ETF", "IEF": "7-10Y Treasury ETF", "SHY": "1-3Y Treasury ETF", "LQD": "IG Corp Bond ETF",
        "HYG": "High Yield ETF", "BND": "Total Bond Market ETF", "AGG": "Agg Bond ETF", "EMB": "EM Bond ETF",
    },
    "Commodities": {
        "GC=F": "Gold", "SI=F": "Silver", "CL=F": "WTI Crude", "BZ=F": "Brent Crude",
        "NG=F": "Natural Gas", "HG=F": "Copper", "ZC=F": "Corn", "ZW=F": "Wheat",
        "KC=F": "Coffee", "PL=F": "Platinum", "PA=F": "Palladium", "ZS=F": "Soybeans",
    },
}

FX_VS_USD = {
    "EUR": ("EURUSD=X", "direct"),
    "GBP": ("GBPUSD=X", "direct"),
    "AUD": ("AUDUSD=X", "direct"),
    "NZD": ("NZDUSD=X", "direct"),
    "JPY": ("USDJPY=X", "inverse"),
    "CHF": ("USDCHF=X", "inverse"),
    "CAD": ("USDCAD=X", "inverse"),
    "CNY": ("USDCNY=X", "inverse"),
}


def extract_close(raw, ticker):
    """Pull a clean Close series out of a yf.download result, whatever shape it came back in."""
    try:
        if isinstance(raw.columns, pd.MultiIndex):
            if ticker in raw.columns.get_level_values(0):
                series = raw[ticker]["Close"]
            elif "Close" in raw.columns.get_level_values(0):
                sub = raw["Close"]
                series = sub[ticker] if ticker in sub.columns else sub.iloc[:, 0]
            else:
                return pd.Series(dtype=float)
        else:
            series = raw["Close"]
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]
        return series.dropna()
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(ttl=900)
def load_category(tickers, period="3mo"):
    """Download daily closes for a list of tickers. Returns {ticker: Series}."""
    raw = yf.download(tickers, period=period, interval="1d", group_by="ticker",
                       progress=False, threads=True)
    return {t: extract_close(raw, t) for t in tickers}


def daily_change(series):
    if len(series) < 2:
        return None, None
    latest = float(series.iloc[-1])
    prev = float(series.iloc[-2])
    pct = (latest / prev) - 1 if prev else None
    return latest, pct


def scaled_chart(series, height=100, interactive=False, show_axes=False):
    """Line chart zoomed to the data's own range instead of a zero baseline."""
    df = series.reset_index()
    df.columns = ["Date", "Value"]
    y_min, y_max = float(df["Value"].min()), float(df["Value"].max())
    pad = (y_max - y_min) * 0.1 or abs(y_max) * 0.01 or 1.0
    y_axis = alt.Axis() if show_axes else None
    x_axis = alt.Axis(format="%b %d") if show_axes else None
    chart = alt.Chart(df).mark_line().encode(
        x=alt.X("Date:T", axis=x_axis, title=None),
        y=alt.Y("Value:Q", scale=alt.Scale(domain=[y_min - pad, y_max + pad]), axis=y_axis, title=None),
        tooltip=["Date:T", "Value:Q"],
    ).properties(height=height)
    if interactive:
        chart = chart.interactive()
    st.altair_chart(chart, use_container_width=True)


PERIOD_OPTIONS = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "5Y": "5y", "Max": "max"}


@st.dialog("Details", width="large")
def ticker_dialog(ticker, label):
    st.subheader(f"{label} ({ticker})")
    lookback = st.radio("Lookback", list(PERIOD_OPTIONS.keys()), index=3, horizontal=True, key=f"period_{ticker}")
    detail = load_category([ticker], period=PERIOD_OPTIONS[lookback])
    series = detail.get(ticker, pd.Series(dtype=float))
    if series.empty:
        st.write("No data available for this ticker right now.")
        return
    latest, pct = daily_change(series)
    m1, m2, m3 = st.columns(3)
    m1.metric("Latest", f"{latest:,.2f}")
    m2.metric("Daily change", f"{pct:+.2%}" if pct is not None else "N/A")
    if len(series) > 21:
        m3.metric("Change over period", f"{(latest / float(series.iloc[0]) - 1):+.2%}")
    scaled_chart(series, height=400, interactive=True, show_axes=True)
    st.caption("Scroll to zoom, drag to pan.")


def render_tile(col, ticker, label, series):
    with col:
        with st.container(border=True):
            st.markdown(f"**{label}**")
            st.caption(ticker)
            if series.empty:
                st.write("No data")
                return
            latest, pct = daily_change(series)
            if latest is None:
                st.write("No data")
                return
            st.metric(" ", f"{latest:,.2f}", f"{pct:+.2%}" if pct is not None else None,
                      label_visibility="collapsed")
            scaled_chart(series.tail(60), height=100)
            if st.button("Expand", key=f"btn_{ticker}", use_container_width=True):
                ticker_dialog(ticker, label)


def render_grid(tickers_map):
    tickers = list(tickers_map.keys())
    data = load_category(tickers)
    cols = st.columns(4)
    for i, ticker in enumerate(tickers):
        render_tile(cols[i % 4], ticker, tickers_map[ticker], data.get(ticker, pd.Series(dtype=float)))


def color_from_value(val, vmin=-0.01, vmax=0.01):
    """Manual red-yellow-green scale, no matplotlib dependency."""
    if pd.isna(val):
        return "background-color: #333333; color: #999999"
    v = max(min(val, vmax), vmin)
    frac = (v - vmin) / (vmax - vmin)
    if frac < 0.5:
        r, g, b = 255, int(255 * (frac / 0.5)), 60
    else:
        r, g, b = int(255 * (1 - (frac - 0.5) / 0.5)), 255, 60
    return f"background-color: rgb({r},{g},{b}); color: black"


def render_currency_matrix():
    st.subheader("Currency Cross Matrix, today's move")
    st.caption("Each cell shows how the row currency moved against the column currency today. "
               "Positive (green) means the row currency strengthened.")

    fx_tickers = [t for t, _ in FX_VS_USD.values()]
    data = load_category(fx_tickers, period="5d")

    changes_vs_usd = {"USD": 0.0}
    for ccy, (ticker, kind) in FX_VS_USD.items():
        series = data.get(ticker, pd.Series(dtype=float))
        _, pct = daily_change(series)
        if pct is None:
            changes_vs_usd[ccy] = None
        elif kind == "direct":
            changes_vs_usd[ccy] = pct
        else:
            changes_vs_usd[ccy] = -pct / (1 + pct) if (1 + pct) != 0 else None

    currencies = ["USD"] + list(FX_VS_USD.keys())
    matrix = pd.DataFrame(index=currencies, columns=currencies, dtype=float)
    for row in currencies:
        for col in currencies:
            a, b = changes_vs_usd.get(row), changes_vs_usd.get(col)
            matrix.loc[row, col] = float("nan") if (a is None or b is None) else (1 + a) / (1 + b) - 1

    styled = matrix.style.format("{:+.2%}", na_rep="N/A")
    try:
        styled = styled.map(color_from_value)
    except AttributeError:
        styled = styled.applymap(color_from_value)

    st.dataframe(styled, use_container_width=True)


def render_category(name, tickers_map):
    st.header(name)
    if name == "Currencies":
        render_currency_matrix()
        st.divider()
    render_grid(tickers_map)


SIDEBAR_CSS = """
<style>
section[data-testid="stSidebar"] .stButton button,
section[data-testid="stSidebar"] .stButton button:hover,
section[data-testid="stSidebar"] .stButton button:active,
section[data-testid="stSidebar"] .stButton button:focus,
section[data-testid="stSidebar"] .stButton button:focus:not(:active),
section[data-testid="stSidebar"] .stButton button:disabled {
    font-size: 20px !important;
    font-weight: 600 !important;
    text-align: left !important;
    background: none !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    padding: 8px 4px !important;
    width: 100% !important;
    opacity: 1 !important;
}
section[data-testid="stSidebar"] .stButton button:hover {
    color: #4da6ff !important;
}
</style>
"""


def render_sidebar():
    st.sidebar.markdown(SIDEBAR_CSS, unsafe_allow_html=True)
    st.sidebar.title("Global Macro")
    st.session_state.setdefault("section", list(CATEGORIES.keys())[0])
    for name in CATEGORIES:
        prefix = "\u27a4  " if st.session_state["section"] == name else "     "
        if st.sidebar.button(f"{prefix}{name}", key=f"nav_{name}"):
            st.session_state["section"] = name
    return st.session_state["section"]


def main():
    section = render_sidebar()
    render_category(section, CATEGORIES[section])


if __name__ == "__main__":
    main()