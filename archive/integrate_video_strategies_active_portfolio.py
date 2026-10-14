"""Add the three A0G14JYYVTk strategies to Active Portfolio V2.

Window: 2025-01-01 through the last available 2026 observation. Existing
portfolio convention: $50k reference capital, 1% maximum planned risk per setup,
integer contracts. Existing multi-level setup split rules remain unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs" / "portfolio_tick_audit_2024_2026" / "risk_normalized_05pct" / "active_portfolio_v2_risk1pct_split_levels" / "trades_risk1pct_split_levels.csv"
VIDEO = ROOT / "outputs" / "video_A0G14JYYVTk_three_strategies" / "all_trades.parquet"
OUT = ROOT / "outputs" / "active_portfolio_v2_plus_video3_2025_2026"

CAPITAL = 50_000.0
RISK_BUDGET = 500.0
MNQ_POINT_VALUE = 2.0
ALL_IN_RT_COST_PER_CONTRACT = 1.0
START = pd.Timestamp("2025-01-01")

RENAME = {
    "Vault Break": "Video — Vault Break",
    "VWAP Pullback": "Video — VWAP Pullback",
    "Overnight Bias ORB": "Video — Overnight Bias ORB",
}


def metric(d: pd.DataFrame) -> dict:
    d = d.sort_values("time").copy()
    if d.empty:
        return {"trades": 0}
    p = d.pnl.to_numpy(float)
    gp, gl = p[p > 0].sum(), -p[p < 0].sum()
    daily_active = d.assign(day=d.time.dt.normalize()).groupby("day").pnl.sum().sort_index()
    days = pd.date_range(d.time.min().normalize(), d.time.max().normalize(), freq="D")
    daily = daily_active.reindex(days, fill_value=0.0)
    eq = np.r_[0.0, daily.cumsum().to_numpy()]
    dd = np.maximum.accumulate(eq)-eq
    sd = daily.std(ddof=1)
    negsd = daily[daily < 0].std(ddof=1)
    months = daily.groupby(daily.index.to_period("M")).sum()
    elapsed_years = max((days[-1]-days[0]).days/365.25, 1/12)
    return {
        "trades": int(len(d)), "net_usd": float(p.sum()),
        "return_on_50k_pct": float(100*p.sum()/CAPITAL),
        "wr_pct": float(100*np.mean(p > 0)), "expectancy_usd": float(p.mean()),
        "pf": float(gp/gl) if gl else np.inf,
        "payoff": float(p[p > 0].mean()/-p[p < 0].mean()) if np.any(p < 0) else np.inf,
        "max_dd_usd": float(dd.max()), "max_dd_pct": float(100*dd.max()/CAPITAL),
        "sharpe": float(np.sqrt(365)*daily.mean()/sd) if sd > 0 else np.nan,
        "sortino": float(np.sqrt(365)*daily.mean()/negsd) if pd.notna(negsd) and negsd > 0 else np.nan,
        "calmar": float((p.sum()/elapsed_years)/dd.max()) if dd.max() > 0 else np.nan,
        "positive_months_pct": float(100*np.mean(months > 0)),
        "best_day_usd": float(daily_active.max()), "worst_day_usd": float(daily_active.min()),
    }


def size_video() -> pd.DataFrame:
    x = pd.read_parquet(VIDEO).copy()
    x["time"] = pd.to_datetime(x.exit_time_utc)
    x = x[x.time >= START].copy()
    x["stop_distance_points"] = np.where(
        x.side.eq("long"), x.entry_price-x.stop_price, x.stop_price-x.entry_price
    )
    x = x[x.stop_distance_points > 0].copy()
    x["risk_per_contract"] = x.stop_distance_points*MNQ_POINT_VALUE + ALL_IN_RT_COST_PER_CONTRACT
    # A $500 setup cap is a hard constraint.  If even one MNQ would exceed it,
    # the signal is not tradable under this portfolio mandate; forcing one
    # contract would silently violate the stated risk limit.
    x = x[x["risk_per_contract"] <= RISK_BUDGET].copy()
    x["quantity"] = np.floor(RISK_BUDGET/x.risk_per_contract).astype(int)
    x["planned_risk"] = x.quantity*x.risk_per_contract
    x["pnl"] = x.net_points*MNQ_POINT_VALUE*x.quantity
    x["strategy"] = x.strategy.map(RENAME)
    x["stop_unit"] = x.stop_distance_points
    x["cost_model"] = "$1/contract embedded in net_points"
    return x[["strategy", "time", "pnl", "quantity", "planned_risk", "stop_unit", "risk_per_contract", "cost_model"]]


def normalize_existing_costs(old: pd.DataFrame) -> pd.DataFrame:
    """Put every legacy family on the same $1 all-in round-trip cost.

    Impulso MNQ and VXN were already net of $1/contract. CVD M6E used $0.48,
    while the MCD source omitted costs. MCD quantities are also recomputed so
    the modelled cost is included in maximum stop risk.
    """
    z = old.copy()
    z["cost_model"] = "already $1/contract"

    cvd = z.strategy.eq("CVD Reversal M6E")
    if cvd.any():
        old_qty = z.loc[cvd, "quantity"].astype(float)
        unit_gross = z.loc[cvd, "pnl"]/old_qty + 0.48
        new_rpc = z.loc[cvd, "stop_unit"]*1.25 + ALL_IN_RT_COST_PER_CONTRACT
        new_qty = np.floor(250.0/new_rpc).astype(int).clip(lower=1)
        z.loc[cvd, "quantity"] = new_qty
        z.loc[cvd, "risk_per_contract"] = new_rpc
        z.loc[cvd, "planned_risk"] = new_qty*new_rpc
        z.loc[cvd, "pnl"] = new_qty*(unit_gross-ALL_IN_RT_COST_PER_CONTRACT)
        z.loc[cvd, "cost_model"] = "raised from $0.48 to $1/contract"

    mcd = z.strategy.eq("MCD Fade PDL/PDH")
    if mcd.any():
        old_qty = z.loc[mcd, "quantity"].astype(float)
        unit_gross = z.loc[mcd, "pnl"]/old_qty
        stop = z.loc[mcd, "stop_unit"].astype(float)
        # Long: one $500-risk leg. Short: one or two $250-risk legs, originally
        # sized at 16 contracts per leg with a $15 stop.
        is_long = stop.eq(20.0)
        legs = pd.Series(np.where(is_long, 1, np.maximum(1, np.rint(old_qty/16))), index=old_qty.index)
        qty_per_leg = np.where(is_long, np.floor(500.0/(stop+1.0)), np.floor(250.0/(stop+1.0)))
        new_qty = (legs.to_numpy()*qty_per_leg).astype(int)
        z.loc[mcd, "quantity"] = new_qty
        z.loc[mcd, "risk_per_contract"] = stop+ALL_IN_RT_COST_PER_CONTRACT
        z.loc[mcd, "planned_risk"] = new_qty*(stop+ALL_IN_RT_COST_PER_CONTRACT)
        z.loc[mcd, "pnl"] = new_qty*(unit_gross-ALL_IN_RT_COST_PER_CONTRACT)
        z.loc[mcd, "cost_model"] = "added $1/contract; quantity recomputed"
    return z


def daily_matrix(d: pd.DataFrame, end: pd.Timestamp) -> pd.DataFrame:
    idx = pd.date_range(START, end, freq="D")
    m = d.assign(day=d.time.dt.normalize()).pivot_table(
        index="day", columns="strategy", values="pnl", aggfunc="sum", fill_value=0.0
    )
    return m.reindex(idx, fill_value=0.0)


def conditional_correlation(matrix: pd.DataFrame) -> pd.DataFrame:
    cols = matrix.columns
    out = pd.DataFrame(np.eye(len(cols)), index=cols, columns=cols)
    for a in cols:
        for b in cols:
            both = (matrix[a] != 0) & (matrix[b] != 0)
            out.loc[a, b] = matrix.loc[both, a].corr(matrix.loc[both, b]) if both.sum() >= 8 else np.nan
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    old = pd.read_csv(BASE, parse_dates=["time"])
    old = normalize_existing_costs(old)
    old = old[old.time >= START].copy()
    new = size_video()
    combined = pd.concat([old, new], ignore_index=True, sort=False).sort_values("time")
    end = combined.time.max().normalize()

    old.to_csv(OUT / "active_v2_trades_2025_2026.csv", index=False)
    new.to_csv(OUT / "video3_sized_trades_2025_2026.csv", index=False)
    combined.to_csv(OUT / "expanded_portfolio_trades_2025_2026.csv", index=False)

    period_masks = {
        "2025": lambda x: x.time.dt.year.eq(2025),
        "2026 partial": lambda x: x.time.dt.year.eq(2026),
        "2025-2026 partial": lambda x: pd.Series(True, index=x.index),
    }
    portfolio_rows = []
    for label, data in [("Active V2", old), ("Active V2 + Video 3", combined)]:
        for period, f in period_masks.items():
            portfolio_rows.append({"portfolio": label, "period": period, **metric(data[f(data)])})
    portfolio_stats = pd.DataFrame(portfolio_rows)
    portfolio_stats.to_csv(OUT / "portfolio_comparison.csv", index=False)

    strategy_rows = []
    for strategy, data in combined.groupby("strategy"):
        for period, f in period_masks.items():
            z = data[f(data)]
            strategy_rows.append({"strategy": strategy, "period": period, **metric(z)})
    strategy_stats = pd.DataFrame(strategy_rows)
    strategy_stats.to_csv(OUT / "strategy_metrics.csv", index=False)

    marginal_sets = {
        "Active V2": old,
        "Active V2 + all Video 3": combined,
        "Active V2 + Vault + Overnight (no VWAP)": pd.concat([old, new[~new.strategy.str.contains("VWAP")]]),
        "Active V2 + Vault only": pd.concat([old, new[new.strategy.str.contains("Vault")]]),
        "Active V2 + Overnight only": pd.concat([old, new[new.strategy.str.contains("Overnight")]]),
        "Active V2 + VWAP only": pd.concat([old, new[new.strategy.str.contains("VWAP")]]),
    }
    marginal = pd.DataFrame([{"configuration": name, **metric(data)} for name, data in marginal_sets.items()])
    marginal.to_csv(OUT / "new_strategies_marginal_comparison.csv", index=False)

    matrix = daily_matrix(combined, end)
    corr = matrix.corr()
    corr_cond = conditional_correlation(matrix)
    matrix.to_csv(OUT / "daily_pnl_matrix.csv")
    corr.to_csv(OUT / "daily_pnl_correlation_zero_filled.csv")
    corr_cond.to_csv(OUT / "correlation_both_strategies_active.csv")

    old_daily = daily_matrix(old, end).sum(axis=1)
    all_daily = matrix.sum(axis=1)
    old_equity = CAPITAL+old_daily.cumsum()
    all_equity = CAPITAL+all_daily.cumsum()
    all_dd = all_equity.cummax()-all_equity

    plt.style.use("seaborn-v0_8-whitegrid")
    fig = plt.figure(figsize=(18, 15))
    gs = fig.add_gridspec(3, 1, height_ratios=[1.35, .65, 1.35])
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(old_equity.index, old_equity, lw=2, color="#64748b", label="Active V2")
    ax1.plot(all_equity.index, all_equity, lw=2.4, color="#0f766e", label="Active V2 + 3 strategie video")
    ax1.set_title("Equity di portafoglio — rischio massimo 1% per setup", fontsize=15, fontweight="bold")
    ax1.set_ylabel("Equity USD (capitale iniziale $50.000)")
    ax1.legend(loc="upper left")
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.fill_between(all_dd.index, 0, -all_dd.values, color="#dc2626", alpha=.72)
    ax2.set_title("Drawdown del portafoglio ampliato")
    ax2.set_ylabel("USD")
    ax3 = fig.add_subplot(gs[2])
    image = ax3.imshow(corr.to_numpy(), cmap="RdBu_r", vmin=-.5, vmax=.5, aspect="auto")
    ax3.set_xticks(range(len(corr.columns)), corr.columns)
    ax3.set_yticks(range(len(corr.index)), corr.index)
    for i in range(len(corr.index)):
        for j in range(len(corr.columns)):
            value = corr.iloc[i, j]
            ax3.text(j, i, f"{value:.2f}", ha="center", va="center",
                     color="white" if abs(value) > .28 else "#111827", fontsize=8)
    cbar = fig.colorbar(image, ax=ax3, fraction=.025, pad=.02)
    cbar.set_label("Correlazione P&L giornaliero")
    ax3.set_title("Correlazioni giornaliere — giorni senza trade = 0", fontsize=14, fontweight="bold")
    ax3.tick_params(axis="x", rotation=35)
    ax3.tick_params(axis="y", rotation=0)
    fig.tight_layout()
    fig.savefig(OUT / "expanded_portfolio_dashboard.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # Individual cumulative contributions, all in portfolio USD after sizing.
    fig, ax = plt.subplots(figsize=(17, 9))
    colors = [plt.get_cmap("tab10")(i) for i in range(len(matrix.columns))]
    for c, color in zip(matrix.columns, colors):
        ax.plot(matrix.index, matrix[c].cumsum(), label=c, lw=1.8, color=color)
    ax.axhline(0, color="black", lw=.8)
    ax.set_title("Contributo cumulato di ogni strategia — 2025-2026 parziale", fontsize=15, fontweight="bold")
    ax.set_ylabel("P&L cumulato USD")
    ax.legend(ncol=2, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "individual_strategy_equities.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    sizing = new.groupby("strategy").agg(
        trades=("quantity", "size"), median_contracts=("quantity", "median"),
        max_contracts=("quantity", "max"), median_planned_risk=("planned_risk", "median"),
        max_planned_risk=("planned_risk", "max")
    ).reset_index()
    sizing.to_csv(OUT / "video3_position_sizing_diagnostics.csv", index=False)

    payload = {
        "capital_usd": CAPITAL, "start": str(START.date()), "last_portfolio_trade": str(combined.time.max()),
        "last_video_data_trade": str(new.time.max()),
        "risk_rule": "$500 maximum intended risk per independent setup; existing same-setup multi-level splits retained",
        "cost_model": "$1 all-in round trip per contract on every strategy; included in stop-risk sizing",
        "warnings": [
            "MCD source ledger originally excluded costs; this report deducts a modelled $1 per contract and recomputes quantity, but it is still not a clean virgin OOS test.",
            "VXN walk-forward portfolio history begins in July 2025.",
            "VWAP Pullback's narrow stops create high contract counts under pure stop-risk sizing; see sizing diagnostics.",
            "Correlations are historical daily P&L correlations, not proof of future independence.",
        ],
        "portfolio_metrics": portfolio_stats.replace({np.nan: None, np.inf: None}).to_dict("records"),
        "marginal_comparison": marginal.replace({np.nan: None, np.inf: None}).to_dict("records"),
        "sizing": sizing.to_dict("records"),
    }
    (OUT / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(portfolio_stats.to_string(index=False))
    print("\nSIZING\n", sizing.to_string(index=False))
    print("\nCORRELATION\n", corr.round(3).to_string())
    print(f"\nOutput: {OUT}")


if __name__ == "__main__":
    main()
