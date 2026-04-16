# CAR Analysis: Tech Layoffs vs. QQQ Benchmark

**Dataset:** `layoffs.csv` mapped to publicly-traded tickers via `TICKER_MAP`.  
**Benchmark:** QQQ (Nasdaq-100 ETF).  
**Event window:** ±20 trading days around each layoff announcement (T = 0).  
**Sample for Panel B:** Target top 70 events by absolute laid-off headcount. The chart title reports the actual displayed count (`N_eff`) and the subtitle states the filter context (`target N`, `available valid events`).

---

## What the Charts Show

### Panel A — Global Baseline (all valid events)

Panel A uses every valid event in the dataset — no filtering, no selection.

**Top subplot — Absolute Returns:** Mean cumulative return of event stocks (orange) against mean QQQ return (dotted dark grey) over the same ±20-day window. Both series are anchored to 0 at T = −20. The legend is removed and replaced by direct labels at T = +20 (`QQQ`, `Stock avg`) in matching line colors to reduce eye travel.

**Bottom subplot — Mean CAR:** Cumulative Abnormal Return, defined as the daily difference between the stock's return and QQQ's return, cumulated from T = −20. CAR removes the market component so that a positive value at T+20 means the stock outperformed QQQ by that percentage, not that it simply went up in a rising market. The mean line is directly labeled at T = +20 (`Mean CAR`). A low-opacity blue shaded ribbon encodes day-level uncertainty as a 95% confidence interval around the mean CAR (`Mean ± 1.96 × SE`), and is drawn without border lines so visual emphasis remains on the mean trajectory. The y = 0 baseline is intentionally emphasized (dark solid line), while other horizontal guides are de-emphasized to lower cognitive load. The y-axis range is tightened to include both the mean path and CI envelope rather than using a broad symmetric bound.

The title is now conclusion-driven (active voice), while the original descriptive statement is retained as a subtitle. This improves immediate interpretability without losing methodological context.

The T = 0 dashed vertical line marks the announcement day. Any pre-announcement drift (slope before T = 0) suggests information leakage or anticipation. The post-announcement slope is the market reaction being studied.

### Panel B — Heatmap: Largest Layoff Events by Headcount (Actual Count Shown)

Each row is one layoff event. Rows are labelled `Company (Mon 'YY)` so that repeat offenders (Meta, Amazon, Microsoft) appear as distinct rows without ambiguity. Events are sorted top-to-bottom from best CAR at T+20 to worst.

**X-axis (columns):** Trading days T = −20 to T+20.  
**Color:** Blue = stock outperformed QQQ (positive CAR); Red = underperformed (negative CAR); White = no excess return.  
**Color scale:** A stepped diverging palette (9 bins) with compressed center thresholds around zero (including narrow bins around ±0.5%) to make small post-event fluctuations legible. Scale remains clamped at ±25% so outliers do not wash out the midrange.

Cell separators are removed (no visible white checkerboard grid), restoring left-to-right continuity in each row. Y-axis labels are darkened (`#555555`) for improved contrast and readability.

Interactive hover is enabled at cell level with: **Company**, **Day (T)**, **Exact CAR (%)**, **Headcount %**, and laid-off count.

The vertical dashed line at T = 0 is aligned with Panel A's T = 0 line, allowing the reader to visually match the aggregate trend to individual rows.

---

## Methodology: Cumulative Abnormal Return (CAR)

For each event:

1. Identify the first trading day on or after the announcement date.
2. Extract the ±20-day return window for both the stock and QQQ.
3. Compute the daily Abnormal Return: `AR(t) = r_stock(t) − r_QQQ(t)`.
4. Compute CAR: `CAR(t) = Σ AR(τ) for τ from −20 to t`, then shift so `CAR(−20) = 0`.
5. Compute event-day uncertainty band: `SE(t) = s(t) / sqrt(N)`, `95% CI(t) = Mean CAR(t) ± 1.96 × SE(t)`, where `s(t)` is the cross-sectional standard deviation of event-level CAR at day `t`.

This is the standard Brown & Warner (1985) market-adjusted returns model. No CAPM beta estimation is used; the benchmark is subtracted directly. This is appropriate for a universe of tech stocks against a tech-heavy index (QQQ) where betas cluster near 1.

---

## Sample Selection: Why Top 70 by Layoff Count?

The heatmap target sample is the **70 events with the largest absolute headcount reductions**, but the rendered row count is `N_eff = min(70, n_total)` after data-validity checks. This criterion is:

- **Economically justified:** Larger layoffs generate stronger analyst attention, more press coverage, and more decisive investor reactions. The signal-to-noise ratio is higher for large events.
- **Pre-declared and reproducible:** Any analyst running this code with the same `layoffs.csv` gets identical rows.
- **Self-documenting:** The selection key (headcount) is independent of the outcome variable (CAR), so the sample cannot be accused of being selected to support a conclusion.

Within that sample, events are sorted by CAR at T+20 (best to worst). This ordering makes it immediately readable whether large layoffs are systematically rewarded or punished, and reveals outliers at either extreme.

---

## Diagnostic Summary: Why Panel A Uses n = 174

Panel A's `n_total` is the number of **valid event windows**, not the raw number of rows in `layoffs.csv`. Using the same pipeline as the app, the sample-construction funnel is:

| Stage | Count | Interpretation |
|-----------|------:|----------------|
| Raw rows in `layoffs.csv` | 4,349 | All layoffs records (public + private, complete + incomplete) |
| Rows with mapped public ticker | 241 | Companies present in `TICKER_MAP` |
| After requiring `Ticker`, `Date`, `Laid_Off` | 190 | Removes rows that cannot be event-studied |
| Remove Twitter events after 27 Oct 2022 delisting | 187 | TWTR no longer trades post-delisting |
| Valid CAR windows used in Panel A | **174** | Final `n_total` shown in Panel A |

Additional drops inside the CAR event-window loop (`187 - 174 = 13`):

- Insufficient ±20-day trading window: 5 events
- Missing returns (`NaN`) inside the event window: 8 events
- No future trading day after event date: 0 events
- Missing ticker/benchmark columns in downloaded panel: 0 events

Therefore, the displayed sample size is:

`n_total = 187 - (5 + 8) = 174`

This is a data-validity filter, not an outcome-based selection on CAR.

---

## Design Decisions

### InfoViz Strategy

Two-tier design: Panel A (all events) anchors the analysis as ground truth. Panel B (top 70) illustrates individual variation in that ground truth. A skeptical reader sees the full population before they see the subset.

### Data-Ink Ratio (Tufte, 1983)

- No sidebar controls; parameters are fixed and declared.
- Legend is removed in Panel A and replaced by direct endpoint labels.
- Non-essential horizontal guides are suppressed in Panel A, while the zero baseline is emphasized where interpretation depends on sign.
- Heatmap cell borders are removed to avoid non-data ink.

### Gestalt Alignment

Both panels share the same x-axis domain and matching axis margins so T = 0 aligns consistently across views. The T = 0 dashed line uses identical styling in both panels, so the eye tracks the aggregate trend (Panel A) down to individual events (Panel B) without instruction.

### Accessible Color Encoding

Stepped red-white-blue encoding is used instead of a continuous diverging gradient:

| Criterion | Continuous diverging (old) | Stepped diverging (new) |
|-----------|-------------|------------|
| Midrange contrast near zero | Often too washed out | Improved through compressed center bins |
| Outlier robustness | Can flatten middle tones | Preserved by fixed ±25% clamp + bins |
| Semantic meaning | Varies by palette | Blue = outperform, Red = underperform |
| Readability for ranking | Subtle gradients can blur row patterns | Step changes improve comparability |

### Dual-Axis Removal

The original Panel A used a dual y-axis (CAR on the left, raw returns on the right). Zero on the CAR axis and zero on the raw return axis did not land on the same pixel plane, creating a visual artifact where the two zero baselines appeared misaligned. Splitting into two stacked subplots with shared x-axis eliminates this entirely — each subplot has one y-axis with one zero baseline.

### 95% CI Band Encoding

Panel A now includes a blue, low-opacity confidence ribbon around the mean CAR to communicate estimation uncertainty at each event day without cluttering the plot with vertical error bars. The ribbon uses the same hue as the mean line, no edge stroke, and a separate legend entry (`Mean CAR (±95% CI)`) to keep semantics explicit while preserving line readability.

---

## Limitations

- The company universe is restricted to publicly-traded firms in `TICKER_MAP`. Private companies (Stripe, Klarna, ByteDance) are excluded — no price data exists, and their absence is non-discretionary.
- QQQ is the market benchmark. A sector-specific benchmark (XLK) or a CAPM-estimated expected return would yield different AR estimates.
- CAR is anchored to zero at T = −20, not T = −1. Pre-event drift is visible but not separated from noise.
- Twitter/X (TWTR) was delisted 27 Oct 2022; post-delisting events are excluded.
- `yf.download` prices are adjusted for splits and dividends (`auto_adjust=True`). Corporate actions within the event window could introduce artefacts for a small number of events.
- Conclusion-style title text is descriptive of current data and may shift slightly as refreshed market data updates CAR endpoints.
