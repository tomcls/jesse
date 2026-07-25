# Research Run #2 — Candidate #1: `R2_KeltnerAsymmetric` (ETH-USD, 4h)

**Date:** 2026-07-23
**Status:** MILESTONE — first config of either research run to satisfy BOTH hard constraints (100-169 trades AND Sharpe > 1.5). Not yet formally accepted; see "Open judgment call" below.

## Mechanism

Asymmetric Keltner-channel breakout with a volatility-expansion gate:

- **Entry long:** close above the upper band of a Keltner(period=25, mult=**2.1**) channel, when ATR(14) > SMA(ATR,20) × 1.0.
- **Entry short:** close below the lower band of a **wider** Keltner(period=25, mult=**2.8**) channel, same volatility gate.
- **Exit:** liquidate when price crosses back through the entered side's own channel midline.
- **Stop:** entry ± 1.35 × ATR(14). Position sized via `risk_to_qty` at 1.5% risk.
- MARKET entries (breakout must be chased — taker fees on every fill, fully modeled).

The asymmetry is the key innovation over the symmetric flagship (`R2_KeltnerBreakoutSelective`, Sharpe 1.3956): longs are the structurally stronger side in this pool (confirmed by a long-only probe reaching Sharpe 1.35 at just 68 trades), so the long channel is tighter (more long entries) while the short channel is wider (only the most extreme breakdowns). Asymmetric long/short parameters were flagged as unexplored in Research Run #1's summary.

## Headline result (window 2022-05-15 → 2025-12-31, Kraken Pro Futures, 3x leverage, 0.05% taker)

| Metric | Value |
|---|---|
| Closed trades | **118** (2.71/month — inside the 2.4-4.0 band) |
| Sharpe (Jesse native, mark-to-market) | **1.5004** |
| Sharpe (independent daily closed-PnL reconstruction) | 1.3077 — see caveat |
| Max drawdown | -14.34% |
| Profit factor | 2.32 |
| Net profit | +265% |
| Win rate | 39.0% |
| Backtest id | `873ceb73-ae31-4144-92d0-0e80300a92d5` |

**Methodology caveat:** the gap between Jesse's native Sharpe (1.50) and my daily-reconstruction cross-check (1.31) is wider on this config than on others tested this run. The 1.5 crossing holds on Jesse's official metric only. 4h positions held across multiple days make the closed-trade daily bucketing coarser, which is the likely cause, but the honest statement is: **1.50 by the official metric, ~1.31-1.45 by conservative alternatives.**

## Robustness — smooth hill, not a razor edge

| Parameter swept | Values | Sharpe |
|---|---|---|
| atr_mult | 1.3 / **1.35** / 1.5 / 1.7 | 1.4786 / **1.5004** / 1.4556 / 1.3854 |
| long_mult | 2.0 / **2.1** / 2.2 | 1.4623 / **1.5004** / 1.4241 |
| short_mult | 2.6 / **2.8** / 3.1 / 3.5 | 1.4134 / 1.4556¹ / 1.4230 / 1.3535 |

¹ at atr_mult=1.5; the short_mult sweep was run before the atr_mult refinement.

Every neighbor within ±10% of every parameter stays above Sharpe 1.35. Contrast with the rejected 30m variant of the symmetric flagship, where a 5% parameter nudge collapsed the signal to zero trades. The honest skill estimate for this region is ≈1.45; 1.5004 is the peak of a smooth hill.

## Cross-symbol replication (strictly identical parameters — report-only, not gating)

| Symbol | Trades | Sharpe | Max DD |
|---|---|---|---|
| **ETH-USD (native)** | **118** | **1.5004** | **-14.3%** |
| BTC-USD | 129 | 0.8137 | -21.3% |
| SOL-USD | 134 | 0.4830 | -19.8% |

Positive on all three symbols, never catastrophic — the signal direction generalizes; the magnitude is ETH-specific. Identical pattern to the symmetric flagship (BTC 0.98, SOL 0.37) and to Research Run #1's finding that ETH is the strongest symbol for the Keltner family.

## Correlation with other candidates (diversity requirement)

Daily-PnL correlation vs the run's #2 candidate `R2_PairsRatioZscore` (ETH/BTC stat-arb, Sharpe 0.5445 @ 104 trades): **0.0135** over 1,337 overlapping days — genuinely independent, far below the 0.3 dedup threshold.

## Monte Carlo (200 scenarios, moving-block bootstrap — session `b241d261-1caa-448c-a0b5-cfce5031a9be`)

| Metric | Original | Worst 5% | Median | Best 5% |
|---|---|---|---|---|
| Sharpe | 1.4843¹ | 1.7139 | 2.4102 | 3.1846 |
| Max drawdown | -14.41% | -21.41% | -15.60% | -10.83% |
| Trade count | 118 | 111 | 125 | 137 |
| Win rate | 38.1% | 33.8% | 39.8% | 46.8% |
| Net profit % | +260% | +224% | +572% | +1363% |

¹ The MC harness's own re-run of the unaltered path gives 1.4843 vs the standalone backtest's 1.5004 — a ±0.02 execution-mode wobble, another honest data point on how thin the 1.5 crossing is.

**Interpretation:**
- The protocol's rejection criterion is "original in the top-5% tail = overfit." That is NOT what we see — the original Sharpe sits **below the entire resampled distribution** (below even the worst-5% at 1.71). This is the same family-wide anomaly observed on both prior MC runs of the symmetric flagship (1h and 4h): the moving-block bootstrap appears to generate *easier* paths for this mechanism than reality, likely because weekly-block shuffling preserves (or amplifies) the vol-expansion patterns the entry needs while the real path's specific regime sequence is harsher. Whatever the cause, **the overfitting signature (lucky-tail original) is absent.**
- Unlike the flagship's MC runs, the trade count (118) now sits normally *within* the resampled distribution (111-137), and max DD (-14.4%) is slightly *better* than the median resampled path (-15.6%) with the worst-5% tail at -21.4% (well inside the -30% catastrophic limit).

## Open judgment call (for Tom)

The acceptance bar is "Sharpe > 1.5." This config clears it by 0.0004 on the official metric, with a robust parameter neighborhood averaging ≈1.45, and a conservative reconstruction at 1.31. Three honest readings:

1. **Accept** — the bar is met on the official metric, the region is robust, the mechanism is validated (p=0.0000 in Run #1), and cross-symbol direction generalizes.
2. **Bench as near-miss** — treat ≈1.45 (neighborhood average) as the true estimate and keep hunting for configs that clear 1.5 with margin.
3. **Accept conditionally** — accept, but weight it accordingly in any portfolio decision and revisit after the single final holdout test.

The autonomous protocol continues either way (7+ more strategies to find); this only affects the accepted-count.

## Provenance

- Family: trend_breakout (Keltner), the only family with Stage-0 p=0.0000 validation from Research Run #1.
- Found at cumulative backtest #94 of Research Run #2 (logged in `reports/ALL-RUNS.jsonl`).
- Full lineage: symmetric flagship (1.3956) → long-only probe (1.3499 @ 68) → asymmetric rounds 1-9 (this config).
