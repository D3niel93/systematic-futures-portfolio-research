# Portfolio dataset contract

Public `trades.csv`: strategy, legacy event time, net modeled pnl (USD), integer quantity, planned_risk and cost_model. No broker account IDs or feed quotes are exported. Every row is a historical backtest outcome, not a live execution.

Dates: 2025-01-02 to 2026-09-02. **Coverage differs by sleeve**, e.g. VXN first fold starts July 2025 and MNQ impulse ends August 2026. Missing sleeve dates are not proof that all sleeves were active on every day.

Legacy portfolio timestamps are preserved without inventing exit timestamps. The public report interprets naive timestamp values as UTC for deterministic bucketing; upstream timezone/date attribution must be independently checked before using those daily statistics for deployment. Per-trade PF/PnL does not depend on that convention.

Correlation uses all weekdays in the combined observed span, zero-filled. Per-sleeve Sharpe uses each sleeve's observed span. Weekdays include holidays; hence these are explicitly business-day proxies, not exchange-calendar or audited NAV ratios. DD is realized/closed-trade; it excludes open adverse excursion.

Fees were normalized upstream to $1 RT per contract. There is no claim this includes all real broker/exchange fees or spread/queue slippage. Planned setup risk uses a fixed $50k reference, not equity compounded sizing. One setup may contain two ledger rows/legs; trade count is row count, not necessarily unique decision count.

Instrument unit checks:
- MNQ: 0.25 tick, $0.50/tick, $2/point.
- M6E: 0.0001 tick, $1.25/tick.
- MCD (micro CAD research): 0.0001 tick, $1/tick.
- 6C (standard CAD demo): 0.00005 tick, $5/tick; ten times MCD dollars per 0.0001 price unit. Do not reuse micro position sizing.

Independent sleeves can overlap MNQ; the native account/instrument gate may suppress overlap. This public aggregate therefore cannot be advertised as achievable live equity.
