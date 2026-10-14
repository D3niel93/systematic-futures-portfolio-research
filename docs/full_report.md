# Complete research report

The Word draft consolidates hypotheses, exact strategy rules, data contracts, annual and monthly results, equity, drawdown, VXN selective prediction, adaptive exits, portfolio dependence, cost stress, native-engine parity evidence and outstanding validation work.

Publication date: 2026-10-14. The report has 34 main sections, 20 tables and 11 figures. The retained private CVD report supplied the research-report structure, not current performance metrics. Its legacy parameterization and tests are not silently transferred to the current strategies.

## Files

- [Word report](../reports/research_report/Systematic_Futures_Research_Report_DRAFT.docx)
- [Day-block bootstrap](../reports/research_report/bootstrap_day_blocks.csv)
- [Monthly PnL and local versus carried drawdown](../reports/research_report/monthly_checked.csv)
- [Structural and numeric checks](../reports/research_report/final_checks.json)
- [Additional figures](../reports/research_report/figures)

The DOCX SHA-256 is `8e9d55b53f9a24cc297b31b8811908bc89762bbfb128dd4a36ff67961c3df395`. The user explicitly authorized an unrendered draft. No Word/LibreOffice page-render QA is claimed. A structural/accessibility check cannot prove clean pagination.

## Statistical interpretation

The report adds circular moving-block resampling of daily portfolio outcomes: block lengths 5, 10 and 20 business days, 10,000 iterations each. Daily aggregation retains contemporaneous strategy outcomes. The report also performs 10,000 permutations of trade order for path drawdown and losing-streak risk. A random permutation cannot change final PnL and is not a random-entry benchmark.

All intervals condition on the already-selected ledger. They do not adjust for multiple parameter searches, establish causal signal alpha, or certify fill quality. The fraction of positive bootstrap samples is not the probability that the strategy has a true edge. Daily bootstrap drawdown and trade-by-trade closed-equity drawdown are different quantities.

The portable robustness script reproduces the day-block experiment from the public ledger using the documented seed. The private Word template, licensed ticks, broker configuration and personal workspace paths are not distributed.

## Corrections and unresolved checks

The VXN values 16.89 and 20.37 points describe **median absolute error**, not mean absolute error. The historical numeric forecast and tradable known-price band anchors differ. CVD native rules and the legacy report differ in PDL/strength conditions and daily boundaries; they require reconciliation. The Word report records these limitations explicitly.

Current results are provisional backtests, not an audited live track record. The report is not a certified prop-account, capacity, or broker-protection simulation.
