import pandas as pd
import yfinance as yf
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Tech Layoffs — CAR Analysis",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── dark style only (no logic changes) ───────────────────────────────────────
st.markdown(
    """
    <style>
    :root {
        --bg-main: #070d1a;
        --bg-panel: #111a2b;
        --bg-panel-soft: #0d1525;
        --bg-plot: #0f192c;
        --border: #263750;
        --text-main: #e6eeff;
        --text-soft: #c3d2f1;
    }

    [data-testid='collapsedControl'] {
        display: none;
    }

    [data-testid='stAppViewContainer'] {
        background:
            radial-gradient(1200px 500px at 6% -10%, rgba(78, 160, 255, 0.16), transparent 55%),
            radial-gradient(1000px 500px at 100% -20%, rgba(79, 109, 255, 0.11), transparent 52%),
            var(--bg-main);
    }

    [data-testid='stHeader'] {
        background: transparent;
    }

    html, body, [class*='css'] {
        color: var(--text-main);
        font-family: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
    }

    [data-testid='stMetric'] {
        border: 1px solid var(--border);
        border-radius: 12px;
        background: var(--bg-panel);
        padding: 0.55rem 0.65rem;
    }

    [data-testid='stMetricLabel'],
    [data-testid='stMetricValue'],
    [data-testid='stMetricDelta'] {
        color: var(--text-main);
    }

    [data-testid='stMarkdownContainer'] p,
    [data-testid='stMarkdownContainer'] li,
    [data-testid='stMarkdownContainer'] h1,
    [data-testid='stMarkdownContainer'] h2,
    [data-testid='stMarkdownContainer'] h3,
    [data-testid='stMarkdownContainer'] h4,
    [data-testid='stMarkdownContainer'] strong,
    [data-testid='stMarkdownContainer'] span {
        color: var(--text-main);
    }

    [data-testid='stCaptionContainer'],
    [data-testid='stCaptionContainer'] p,
    .stCaption,
    .stCaption p {
        color: var(--text-soft) !important;
    }

    [data-testid='stMultiSelect'] > div,
    [data-testid='stSelectbox'] > div,
    [data-testid='stRadio'] > div,
    [data-testid='stNumberInput'] > div {
        background: var(--bg-panel-soft);
        border-color: var(--border);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

WINDOW_PRE = 90
WINDOW_POST = 60
BENCHMARK = "QQQ"
N = 70  # top N events by layoff count

THEME = {
    "page_bg": "#070d1a",
    "panel_bg": "#111a2b",
    "plot_bg": "#0f192c",
    "grid": "rgba(159, 179, 218, 0.18)",
    "text": "#e6eeff",
    "subtext": "#c3d2f1",
    "border": "#263750",
    "accent_blue": "#4ea0ff",
    "accent_orange": "#e7b15e",
    "accent_gray": "#9aa6bd",
}

TICKER_MAP = {
    "Amazon": "AMZN",
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Google": "GOOGL",
    "Meta": "META",
    "Tesla": "TSLA",
    "Nvidia": "NVDA",
    "Netflix": "NFLX",
    "Oracle": "ORCL",
    "IBM": "IBM",
    "Intel": "INTC",
    "Cisco": "CSCO",
    "Salesforce": "CRM",
    "Adobe": "ADBE",
    "SAP": "SAP",
    "Qualcomm": "QCOM",
    "Dell": "DELL",
    "HP": "HPQ",
    "Uber": "UBER",
    "Lyft": "LYFT",
    "Airbnb": "ABNB",
    "Spotify": "SPOT",
    "Shopify": "SHOP",
    "Zoom": "ZM",
    "Snap": "SNAP",
    "Pinterest": "PINS",
    "Robinhood": "HOOD",
    "Coinbase": "COIN",
    "PayPal": "PYPL",
    "eBay": "EBAY",
    "Dropbox": "DBX",
    "DocuSign": "DOCU",
    "Twilio": "TWLO",
    "Workday": "WDAY",
    "ServiceNow": "NOW",
    "Palantir": "PLTR",
    "Unity": "U",
    "Roblox": "RBLX",
    "EA": "EA",
    "Autodesk": "ADSK",
    "Okta": "OKTA",
    "Zendesk": "ZEN",
    "HubSpot": "HUBS",
    "Atlassian": "TEAM",
    "Cloudflare": "NET",
    "Datadog": "DDOG",
    "Snowflake": "SNOW",
    "Palo Alto Networks": "PANW",
    "CrowdStrike": "CRWD",
    "MongoDB": "MDB",
    "Block": "SQ",
    "Twitter": "TWTR",
}

# ═══════════════════════════════════════════════════════════════════════════════
#  DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════


@st.cache_data(show_spinner="Loading data…")
def load_data():
    df_raw = pd.read_csv("layoffs.csv")
    df_raw["Date"] = pd.to_datetime(df_raw["Date"], errors="coerce")
    df_raw["Laid_Off"] = pd.to_numeric(df_raw["Laid_Off"], errors="coerce")
    df_raw["Percentage"] = pd.to_numeric(df_raw["Percentage"], errors="coerce")
    df_raw["Ticker"] = df_raw["Company"].map(TICKER_MAP)

    df_events = df_raw.dropna(subset=["Ticker", "Date", "Laid_Off"]).copy()
    df_events = df_events[
        ~((df_events["Company"] == "Twitter") & (df_events["Date"] > pd.Timestamp("2022-10-27")))
    ].reset_index(drop=True)

    tickers = sorted(df_events["Ticker"].unique().tolist()) + [BENCHMARK]
    start_date = (df_events["Date"].min() - pd.Timedelta(days=140)).strftime("%Y-%m-%d")
    end_date = (pd.Timestamp.now() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    raw = yf.download(tickers, start=start_date, end=end_date, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        raise RuntimeError("yf.download returned no data")
    prices = raw["Close"]
    returns = prices.pct_change(fill_method=None)

    if returns.index.tz is not None:
        returns.index = returns.index.tz_localize(None)
    if prices.index.tz is not None:
        prices.index = prices.index.tz_localize(None)

    return df_events, prices, returns


@st.cache_data(show_spinner="Computing CAR…")
def compute_cars(_df_events, _prices, _returns):
    all_cars, all_labels, all_laid_off = [], [], []
    all_price_windows, all_bench_windows = [], []
    all_headcount_pct = []

    for _, row in _df_events.iterrows():
        ticker, event_date = row["Ticker"], row["Date"]

        if event_date not in _returns.index:
            future = _returns.index[_returns.index >= event_date]
            if len(future) == 0:
                continue
            event_date = future[0]

        loc = _returns.index.get_loc(event_date)
        if loc < WINDOW_PRE or loc + WINDOW_POST >= len(_returns):
            continue

        win_r = _returns.iloc[loc - WINDOW_PRE : loc + WINDOW_POST + 1]
        if ticker not in win_r.columns or BENCHMARK not in win_r.columns:
            continue

        tr, br = win_r[ticker], win_r[BENCHMARK]
        if tr.isna().any() or br.isna().any():
            continue

        car = (tr - br).cumsum()
        car = car - car.iloc[0]

        cum_stock = tr.cumsum() - tr.cumsum().iloc[0]
        cum_bench = br.cumsum() - br.cumsum().iloc[0]

        all_cars.append(car.values)
        all_price_windows.append(cum_stock.values)
        all_bench_windows.append(cum_bench.values)
        all_labels.append(f"{row['Company']}  {event_date.strftime('%Y-%m-%d')}")
        all_laid_off.append(int(row["Laid_Off"]))
        all_headcount_pct.append(float(row["Percentage"]) if pd.notna(row["Percentage"]) else np.nan)

    car_matrix = np.array(all_cars)
    price_matrix = np.array(all_price_windows)
    bench_matrix = np.array(all_bench_windows)
    days = np.arange(-WINDOW_PRE, WINDOW_POST + 1)

    return (
        car_matrix,
        price_matrix,
        bench_matrix,
        days,
        all_labels,
        all_laid_off,
        all_headcount_pct,
    )


df_events, prices, returns = load_data()
(
    car_matrix,
    price_matrix,
    bench_matrix,
    days,
    all_labels,
    all_laid_off,
    all_headcount_pct,
) = compute_cars(df_events, prices, returns)
n_total = len(car_matrix)

ALIGN_LEFT_MARGIN = 210
ALIGN_RIGHT_MARGIN = 120
X_AXIS_RANGE = [-WINDOW_PRE - 0.5, WINDOW_POST + 0.5]
X_AXIS_DOMAIN = [0.0, 0.92]

st.title("Tech Layoffs and Stock Performance: Early Signal or False Cure?")
st.markdown(
    "This dashboard evaluates whether major tech layoffs are preceded by market warning signs "
    "and whether large headcount cuts reliably improve post-announcement stock performance."
)

st.markdown("#### Audience Guide")
guide_col_a, guide_col_b = st.columns(2)
with guide_col_a:
    st.markdown(
        "**How to read Panel A**\n"
        "1. Orange line (CR): average cumulative stock return.\n"
        "2. Dotted gray line: benchmark cumulative return (QQQ).\n"
        "3. Blue line (CAR): stock minus benchmark, isolating company-specific performance.\n"
        "4. Light-blue band: 95% confidence interval around mean CAR."
    )
with guide_col_b:
    st.markdown(
        "**How to read Panel B**\n"
        "1. Each row is one layoff event among the top 70 by layoff count.\n"
        "2. Rows are ranked by T+60 CAR (best to worst).\n"
        "3. Blue means positive CAR, red means negative CAR, white is near zero.\n"
        "4. The middle rows approximate the median outcome."
    )

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
#  PANEL A — Mean CAR (all events)
# ═══════════════════════════════════════════════════════════════════════════════

mean_car = car_matrix.mean(axis=0)
mean_stock = price_matrix.mean(axis=0)
mean_bench = bench_matrix.mean(axis=0)

if n_total > 1:
    std_car = car_matrix.std(axis=0, ddof=1)
else:
    std_car = np.zeros_like(mean_car)

se_car = std_car / np.sqrt(n_total)
ci_margin = 1.96 * se_car
lower_bound = mean_car - ci_margin
upper_bound = mean_car + ci_margin

mean_car_pct = mean_car * 100
lower_bound_pct = lower_bound * 100
upper_bound_pct = upper_bound * 100

car_min = float(lower_bound_pct.min())
car_max = float(upper_bound_pct.max())
car_span = max(car_max - car_min, 0.2)
car_pad = max(0.08 * car_span, 0.12)
car_ymin = min(np.floor((car_min - car_pad) * 10) / 10, -0.1)
car_ymax = max(np.ceil((car_max + car_pad) * 10) / 10, 0.1)

mean_car_t60 = float(mean_car_pct[-1])

zero_day_idx = int(np.where(days == 0)[0][0])
trough_idx = int(np.argmin(mean_car))
trough_day = int(days[trough_idx])
trough_car_pct = float(mean_car_pct[trough_idx])

recovery_start_idx = trough_idx
for idx in range(trough_idx + 1, len(mean_car) - 2):
    if (
        mean_car[idx] > mean_car[idx - 1]
        and mean_car[idx + 1] > mean_car[idx]
        and mean_car[idx + 2] > mean_car[idx + 1]
    ):
        recovery_start_idx = idx
        break
recovery_start_day = int(days[recovery_start_idx])

ci_width_pct = (upper_bound - lower_bound) * 100
pre_ci_width = float(ci_width_pct[days < 0].mean()) if np.any(days < 0) else np.nan
post_ci_width = float(ci_width_pct[days >= 0].mean()) if np.any(days >= 0) else np.nan
ci_widen_ratio = post_ci_width / pre_ci_width if pre_ci_width > 0 else np.nan

post_slope = (mean_car_pct[-1] - mean_car_pct[zero_day_idx]) / max(WINDOW_POST, 1)

stock_end_pct = float(mean_stock[-1] * 100)
bench_end_pct = float(mean_bench[-1] * 100)
top_label_gap = abs(stock_end_pct - bench_end_pct)

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
metric_col1.metric("Valid events", f"{n_total}")
metric_col2.metric("Mean CAR at T+60", f"{mean_car_t60:+.2f}%")
metric_col3.metric("Panel A trough", f"T={trough_day}", f"{trough_car_pct:+.2f}%")
if np.isfinite(ci_widen_ratio):
    metric_col4.metric(
        "CI width (post/pre)",
        f"{ci_widen_ratio:.2f}x",
        f"{post_ci_width:.2f}pp vs {pre_ci_width:.2f}pp",
    )
else:
    metric_col4.metric("CI width (post/pre)", "N/A")

# Avoid overlap when endpoint values are close by separating labels in pixel space.
MIN_LABEL_GAP_PCT = 0.35
if top_label_gap < MIN_LABEL_GAP_PCT:
    label_push = 14
    if stock_end_pct >= bench_end_pct:
        stock_label_shift, bench_label_shift = label_push, -label_push
    else:
        stock_label_shift, bench_label_shift = -label_push, label_push
    stock_label_xshift, bench_label_xshift = 14, 8
else:
    stock_label_shift = bench_label_shift = 0
    stock_label_xshift = bench_label_xshift = 8

fig_a = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.08,
    row_heights=[0.42, 0.58],
)

fig_a.add_trace(
    go.Scatter(
        x=days,
        y=mean_stock * 100,
        name="Mean CR",
        legendrank=1,
        line=dict(color=THEME["accent_orange"], width=1.9),
        hovertemplate="Day %{x}: Avg stock %{y:.2f}%<extra></extra>",
        showlegend=True,
    ),
    row=1,
    col=1,
)
fig_a.add_trace(
    go.Scatter(
        x=days,
        y=mean_bench * 100,
        name="Benchmark (QQQ)",
        legendrank=2,
        line=dict(color=THEME["accent_gray"], width=1.5, dash="dot"),
        hovertemplate="Day %{x}: QQQ %{y:.2f}%<extra></extra>",
        showlegend=True,
    ),
    row=1,
    col=1,
)

fig_a.add_trace(
    go.Scatter(
        x=days,
        y=upper_bound * 100,
        mode="lines",
        line=dict(width=0, color="rgba(78, 160, 255, 0)"),
        hoverinfo="skip",
        showlegend=False,
    ),
    row=2,
    col=1,
)
fig_a.add_trace(
    go.Scatter(
        x=days,
        y=lower_bound * 100,
        mode="lines",
        line=dict(width=0, color="rgba(78, 160, 255, 0)"),
        fill="tonexty",
        fillcolor="rgba(78, 160, 255, 0.22)",
        name="Mean CAR (±95% CI)",
        legendrank=3,
        hovertemplate="Day %{x}: 95% CI [%{y:.3f}%, %{customdata:.3f}%]<extra></extra>",
        customdata=upper_bound * 100,
        showlegend=True,
    ),
    row=2,
    col=1,
)
fig_a.add_trace(
    go.Scatter(
        x=days,
        y=mean_car * 100,
        name="Mean CAR",
        legendrank=4,
        line=dict(color=THEME["accent_blue"], width=2.2),
        hovertemplate="Day %{x}: %{y:.3f}%<extra></extra>",
        showlegend=True,
    ),
    row=2,
    col=1,
)

fig_a.add_vline(x=0, line=dict(color="rgb(255, 255, 255)", dash="solid", width=2.8))
fig_a.add_shape(
    type="line",
    x0=-WINDOW_PRE,
    x1=WINDOW_POST,
    y0=0,
    y1=0,
    line=dict(color="#a8b4cc", width=0.9),
    row=1,
    col=1,
)
fig_a.add_shape(
    type="line",
    x0=-WINDOW_PRE,
    x1=WINDOW_POST,
    y0=0,
    y1=0,
    line=dict(color="#b7c5df", width=1.25),
    row=2,
    col=1,
)

fig_a.add_annotation(
    x=WINDOW_POST,
    y=bench_end_pct,
    xref="x",
    yref="y",
    text="QQQ",
    showarrow=False,
    xanchor="left",
    yanchor="middle",
    xshift=bench_label_xshift,
    yshift=bench_label_shift,
    font=dict(color=THEME["accent_gray"], size=12),
)
fig_a.add_annotation(
    x=WINDOW_POST,
    y=stock_end_pct,
    xref="x",
    yref="y",
    text="MEAN CR",
    showarrow=False,
    xanchor="left",
    yanchor="middle",
    xshift=stock_label_xshift,
    yshift=stock_label_shift,
    font=dict(color=THEME["accent_orange"], size=12),
)
fig_a.add_annotation(
    x=WINDOW_POST,
    y=float(mean_car[-1] * 100),
    xref="x2",
    yref="y2",
    text="Mean CAR",
    showarrow=False,
    xanchor="left",
    yanchor="middle",
    xshift=8,
    font=dict(color=THEME["accent_blue"], size=12),
)

fig_a.update_layout(
    title=dict(
        text=(
            f"<span style='color:{THEME['text']}'>"
            "Mean Cumulative Return (CR) and Cumulative Abnormal Return (CAR) Around Tech Layoff Announcements "
            f"(T={-WINDOW_PRE} to T=+{WINDOW_POST} Trading Days)</span>"
            f"<br><sup style='color:{THEME['subtext']}'>"
            f"Sample Size: {n_total} Events | Comparison: Stock Mean vs. Benchmark ({BENCHMARK}) | "
            "Additional Metric: CAR 95% Confidence Interval</sup>"
        ),
        font=dict(size=14, color=THEME["text"]),
        x=0.5,
        xanchor="center",
    ),
    height=600,
    margin=dict(l=ALIGN_LEFT_MARGIN, r=ALIGN_RIGHT_MARGIN, t=78, b=50),
    showlegend=True,
    legend=dict(
        traceorder="normal",
        orientation="v",
        yanchor="bottom",
        y=0.02,
        xanchor="left",
        x=1.02,
        bgcolor="rgba(10, 17, 30, 0.88)",
        bordercolor=THEME["border"],
        borderwidth=1,
        font=dict(color=THEME["text"]),
    ),
    font=dict(color=THEME["text"], family="IBM Plex Sans, Avenir Next, Segoe UI, sans-serif"),
    plot_bgcolor=THEME["plot_bg"],
    paper_bgcolor=THEME["panel_bg"],
    hovermode="x unified",
)
fig_a.update_xaxes(
    range=X_AXIS_RANGE,
    tickmode="linear",
    dtick=5,
    gridcolor=THEME["grid"],
    domain=X_AXIS_DOMAIN,
    row=1,
    col=1,
    showline=True,
    linecolor=THEME["border"],
    tickfont=dict(color=THEME["subtext"]),
    title_font=dict(color=THEME["text"]),
)
fig_a.update_xaxes(
    title_text="Trading Days Relative to Announcement  (T = 0)",
    range=X_AXIS_RANGE,
    tickmode="linear",
    dtick=5,
    gridcolor=THEME["grid"],
    domain=X_AXIS_DOMAIN,
    row=2,
    col=1,
    showline=True,
    linecolor=THEME["border"],
    tickfont=dict(color=THEME["subtext"]),
    title_font=dict(color=THEME["text"]),
)
fig_a.update_yaxes(
    title_text="Cumulative Return (%)",
    tickformat=".1f",
    showgrid=False,
    zeroline=False,
    row=1,
    col=1,
    showline=True,
    linecolor=THEME["border"],
    tickfont=dict(color=THEME["subtext"]),
    title_font=dict(color=THEME["text"]),
)
fig_a.update_yaxes(
    title_text="Cumulative Abnormal Return (CAR, %)",
    tickformat=".2f",
    showgrid=False,
    zeroline=False,
    range=[car_ymin, car_ymax],
    row=2,
    col=1,
    showline=True,
    linecolor=THEME["border"],
    tickfont=dict(color=THEME["subtext"]),
    title_font=dict(color=THEME["text"]),
)

st.plotly_chart(fig_a, use_container_width=True)

if np.isfinite(ci_widen_ratio):
    ci_summary = (
        f"Post-announcement uncertainty is much larger: average CI width after T=0 is "
        f"{ci_widen_ratio:.2f}x the pre-announcement width."
    )
else:
    ci_summary = "CI widening could not be summarized due to limited variation in the pre-announcement window."

st.markdown("#### Panel A Key Insights")
st.markdown(
    f"1. The mean CAR shows a U-shape: it falls below zero and bottoms around T={trough_day} at {trough_car_pct:+.2f}%.\n"
    f"2. Recovery begins around T={recovery_start_day}, with post-announcement drift averaging {post_slope:+.3f} percentage points per trading day.\n"
    f"3. {ci_summary}\n"
    "4. Interpretation: the average pattern suggests a potential pre-layoff underperformance signal, but dispersion is high and firm-level outcomes vary widely."
)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
#  PANEL B — Heatmap: top 70 by layoff count, sorted best→worst CAR at T+60
# ═══════════════════════════════════════════════════════════════════════════════

car_final = car_matrix[:, -1]

# top 70 by layoff count
pool_idx = np.argsort(all_laid_off)[::-1][: min(N, n_total)]
# within that pool, order best → worst CAR at T+60
order = np.argsort(car_final[pool_idx])[::-1]
ranked_idx = pool_idx[order]
N_eff = len(ranked_idx)

sub_cars = car_matrix[ranked_idx]
sub_labels = [all_labels[i] for i in ranked_idx]
sub_counts = [all_laid_off[i] for i in ranked_idx]
sub_headcount_pct = [all_headcount_pct[i] for i in ranked_idx]

t60_pool_pct = sub_cars[:, -1] * 100
median_t60 = float(np.median(t60_pool_pct))
mean_t60 = float(np.mean(t60_pool_pct))
positive_share = float((t60_pool_pct > 0).mean() * 100)
negative_share = float((t60_pool_pct < 0).mean() * 100)


def _format_event_outcome(label: str, car_val: float) -> str:
    company, date_str = label.split("  ", 1)
    return f"{company} ({date_str}) {car_val:+.1f}%"


top_examples = [_format_event_outcome(sub_labels[idx], t60_pool_pct[idx]) for idx in range(min(3, N_eff))]
bottom_examples = [
    _format_event_outcome(sub_labels[idx], t60_pool_pct[idx]) for idx in range(N_eff - 1, max(-1, N_eff - 4), -1)
]


def _best_company_t60(company: str):
    values = [t60_pool_pct[idx] for idx, label in enumerate(sub_labels) if label.startswith(f"{company}  ")]
    return float(max(values)) if values else None


meta_t60 = _best_company_t60("Meta")
dell_t60 = _best_company_t60("Dell")

tesla_positions = [idx for idx, lbl in enumerate(sub_labels) if lbl.startswith("Tesla  ")]
tesla_summary = None
if tesla_positions:
    tesla_idx = tesla_positions[0]
    tesla_rank = tesla_idx + 1
    tesla_t60 = float(t60_pool_pct[tesla_idx])
    tesla_summary = (
        f"Tesla appears at rank {tesla_rank}/{N_eff} with a T+60 CAR of {tesla_t60:+.1f}%, showing that even the largest layoff among the 167 samples—a reduction of 14,000 people—does not automatically produce a market recovery."
    )


def _event_label(lbl: str) -> str:
    company, date_str = lbl.split("  ", 1)
    try:
        month_abbr = pd.Timestamp(date_str).strftime("%d %b '%y")
    except Exception:
        month_abbr = date_str
    return f"{company} ({month_abbr})"


y_labels = [f"{idx + 1:02d}. {_event_label(lbl)}" for idx, lbl in enumerate(sub_labels)]

# hover text — shape [e_idx][d_idx] matches z[e_idx][d_idx]
hover_text = []
for e_idx in range(N_eff):
    company, date_str = sub_labels[e_idx].split("  ", 1)
    if pd.notna(sub_headcount_pct[e_idx]):
        headcount_pct_text = f"{sub_headcount_pct[e_idx] * 100:.1f}%"
    else:
        headcount_pct_text = "N/A"

    row_texts = []
    for d_idx, d in enumerate(days):
        car_val = sub_cars[e_idx, d_idx] * 100
        row_texts.append(
            f"Company: <b>{company}</b><br>"
            f"Date: {date_str}<br>"
            f"Day (T): {d:+d}<br>"
            f"Exact CAR (%): {car_val:+.2f}%<br>"
            f"Headcount %: {headcount_pct_text}<br>"
            f"Laid off (count): {sub_counts[e_idx]:,}"
        )
    hover_text.append(row_texts)

COLOR_BOUNDS = [-40, -20, -10, -4, -1, 1, 4, 10, 20, 40]
COLOR_STEPS = [
    "#5f0f24",
    "#8f1d36",
    "#c54e4e",
    "#e4937c",
    "#c8d7ee",
    "#8fc3e5",
    "#59a5d4",
    "#2f81be",
    "#15558f",
]


def _build_stepped_colorscale(bounds, colors):
    zmin, zmax = bounds[0], bounds[-1]
    span = zmax - zmin
    stepped = []
    for idx, color in enumerate(colors):
        left = (bounds[idx] - zmin) / span
        right = (bounds[idx + 1] - zmin) / span
        stepped.extend([[left, color], [right, color]])
    return stepped


COLOR_CLAMP = float(COLOR_BOUNDS[-1])
HEATMAP_COLORSCALE = _build_stepped_colorscale(COLOR_BOUNDS, COLOR_STEPS)

fig_b = go.Figure(
    go.Heatmap(
        z=sub_cars * 100,
        x=days,
        y=y_labels,
        colorscale=HEATMAP_COLORSCALE,
        zmid=0,
        zmin=-COLOR_CLAMP,
        zmax=COLOR_CLAMP,
        text=hover_text,
        hovertemplate="%{text}<extra></extra>",
        colorbar=dict(
            title=dict(text="CAR (%)", side="right", font=dict(color=THEME["text"])),
            tickformat=".0f",
            tickvals=[-40, -20, -10, -4, 0, 4, 10, 20, 40],
            lenmode="fraction",
            len=0.80,
            thickness=14,
            x=0.95,
            xanchor="left",
            tickfont=dict(color=THEME["subtext"]),
        ),
        xgap=0,
        ygap=0,
    )
)

fig_b.add_vline(x=0, line=dict(color="rgb(255, 255, 255)", dash="solid", width=2.8))

fig_b.update_layout(
    title=dict(
        text=(
            f"<span style='color:{THEME['text']}'>"
            "Time-Series Heatmap of Cumulative Abnormal Return (CAR) for Major Tech Layoff Events"
            "</span>"
            f"<br><sup style='color:{THEME['subtext']}'>"
            f"Data Scope: Top {N_eff} Events by Absolute Headcount Reduction | Sorting Rule: Descending Order by T+60 CAR</sup>"
            f"<br><sup style='color:{THEME['subtext']}'>"
            f"Window: T={-WINDOW_PRE} to T=+{WINDOW_POST} | Target N = {N} | Available Valid Events = {n_total}</sup>"
        ),
        font=dict(size=14, color=THEME["text"]),
        x=0.5,
        xanchor="center",
    ),
    height=max(700, N_eff * 16 + 160),
    margin=dict(l=ALIGN_LEFT_MARGIN, r=ALIGN_RIGHT_MARGIN, t=78, b=55),
    font=dict(color=THEME["text"], family="IBM Plex Sans, Avenir Next, Segoe UI, sans-serif"),
    plot_bgcolor=THEME["plot_bg"],
    paper_bgcolor=THEME["panel_bg"],
    xaxis=dict(
        title=dict(
            text="Trading Days Relative to Announcement  (T = 0)",
            font=dict(color=THEME["text"]),
        ),
        tickmode="linear",
        dtick=5,
        gridcolor=THEME["grid"],
        range=X_AXIS_RANGE,
        domain=X_AXIS_DOMAIN,
        showline=True,
        linecolor=THEME["border"],
        tickfont=dict(color=THEME["subtext"]),
    ),
    yaxis=dict(
        autorange="reversed",
        tickfont=dict(size=10, color=THEME["subtext"]),
        showline=True,
        linecolor=THEME["border"],
    ),
)

st.plotly_chart(fig_b, use_container_width=True)

if meta_t60 is not None and dell_t60 is not None:
    outlier_summary = f"Meta ({meta_t60:+.1f}%) and Dell ({dell_t60:+.1f}%) are examples of strong right-tail outliers."
else:
    outlier_summary = "Top-ranked events act as right-tail outliers and can pull the average above the median."

st.markdown("#### Panel B Key Insights")
st.markdown(
    f"1. Median T+60 CAR across the top {N_eff} layoff events is {median_t60:+.2f}% (near zero).\n"
    f"2. Mean T+60 CAR is {mean_t60:+.2f}%, higher than the median, indicating outlier-driven skew.\n"
    f"3. By T+60, {positive_share:.1f}% of events are positive and {negative_share:.1f}% are negative, which is close to a coin-flip distribution.\n"
    f"4. {outlier_summary}"
)

if top_examples:
    st.markdown("**Top positive outliers (T+60 CAR):** " + " | ".join(top_examples))
if bottom_examples:
    st.markdown("**Weakest outcomes (T+60 CAR):** " + " | ".join(bottom_examples))
if tesla_summary:
    st.markdown("**Case example:** " + tesla_summary)

st.markdown("#### Final Takeaways")
takeaway_col1, takeaway_col2 = st.columns(2)
with takeaway_col1:
    st.markdown(
        "**For employees**\n"
        "- A plunging stock is not a guaranteed layoff trigger, but persistent negative CAR is still a meaningful early risk signal.\n"
        "- Practical implication: deep, sustained underperformance can justify updating your resume and building options."
    )
with takeaway_col2:
    st.markdown(
        "**For stakeholders**\n"
        "- Layoffs are not a universal stock-price fix; median outcomes are near zero.\n"
        "- Practical implication: restructuring should be judged on long-term fundamentals, not short-term headline effects."
    )

st.caption(
    "Method note: This is an event-study association analysis (not causal proof). "
    "CAR is measured relative to QQQ over T=-90 to T=+60 trading days."
)
