# CAR Visualization Facts (Current App Behavior)

## Scope and Inputs

- Source table: `layoffs.csv`
- Benchmark ticker: `QQQ`
- Event window: +/-20 trading days (`WINDOW = 20`)
- Heatmap target size: top 70 events by laid-off count (`N = 70`)
- Price source: `yfinance.download(..., auto_adjust=True)`

Data preparation steps in the app:

1. Parse `Date` as datetime and coerce invalid values to null.
2. Parse `Laid_Off` and `Percentage` as numeric and coerce invalid values to null.
3. Map `Company` to ticker using `TICKER_MAP`.
4. Keep rows with non-null `Ticker`, `Date`, and `Laid_Off`.
5. Exclude Twitter rows after 2022-10-27.

The download date range is built at runtime:

- Start: minimum event date minus 90 calendar days
- End: current timestamp plus 1 day

## Event-Window Construction

For each filtered event row:

1. If event date is not a trading day, move to the first trading day on or after that date.
2. Require a full +/-20-day return window in the benchmark/stock return index.
3. Require both stock and benchmark columns in the return window.
4. Drop the event if either return series has any missing value in the window.
5. Compute daily abnormal return as stock return minus benchmark return.
6. Compute CAR as cumulative abnormal return, then shift so T=-20 equals 0.
7. Compute cumulative stock return and cumulative benchmark return, each anchored to 0 at T=-20.

Saved event metadata per valid row:

- Label: `Company  YYYY-MM-DD`
- Laid-off count: integer
- Headcount percentage: float (or NaN)

`n_total` in the charts is the number of events that pass all checks above.

## Panel A Facts (All Valid Events)

Panel A uses all valid events (`n_total`) and has two stacked subplots sharing the same x-axis (`-20..20`).

Top subplot traces:

- Mean cumulative stock return (orange solid line)
- Mean cumulative benchmark return (gray dotted line)

Bottom subplot traces:

- Mean CAR (blue line)
- 95% CI band around mean CAR, calculated as `Mean +/- 1.96 * SE`

Visual elements in Panel A:

- Dashed vertical line at T=0
- Horizontal y=0 line in top subplot (light gray)
- Horizontal y=0 line in bottom subplot (dark, thicker)
- Endpoint text labels at T=20: `QQQ`, `MEAN CR`, `Mean CAR`
- Legend is enabled and shown to the right
- Hover mode is `x unified`

Bottom subplot y-range is computed from CI min/max with dynamic padding.

## Panel B Facts (Heatmap)

Selection and ordering:

1. Start from all valid events used in Panel A.
2. Select top events by laid-off count in descending order, limited to 70.
3. Within that subset, sort rows by T+20 CAR in descending order (best to worst).

Displayed row count:

- `N_eff = min(70, n_total)`

Heatmap encoding:

- X-axis: trading days T=-20 to T=20
- Z values: CAR in percent
- Y labels: ranked rows with formatted date (`01. Company (DD Mon 'YY)`)
- Color scale: stepped diverging bins with bounds
	`[-25, -12, -6, -2, -0.5, 0.5, 2, 6, 12, 25]`
- Clamp: `zmin=-25`, `zmax=25`, midpoint at 0
- Cell gaps: `xgap=0`, `ygap=0`
- Dashed vertical line at T=0

Hover fields per cell:

- Company
- Date
- Day (T)
- Exact CAR (%)
- Headcount %
- Laid off (count)

## Layout and Styling Facts

- Streamlit page is wide layout with collapsed sidebar.
- Sidebar collapse toggle button is hidden via CSS.
- Common x-range in both panels: `[-20.5, 20.5]`
- Common x-domain in both panels: `[0.0, 0.92]`
- Common margins in both panels: left `210`, right `120`
- Background color: `#FAFAFA` for plot and paper
- Heatmap y-axis is reversed so rank 1 appears at the top
- Heatmap height rule: `max(700, N_eff * 16 + 160)`

## Runtime-Dependent Outputs

- `n_total` and `N_eff` are computed at runtime and may change when input data or market data updates.
- Mean CAR paths and final ranking depend on current downloaded price history.

## Current Implementation Constraints

- Company coverage is limited to firms present in `TICKER_MAP`.
- Private companies without tradable tickers are excluded.
- Benchmark is fixed to `QQQ` (no CAPM beta model in code).
- Twitter rows after delisting cutoff (2022-10-27) are excluded by rule.
