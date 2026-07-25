# Pipeline Dry Run — Results (v2, re-run on clean data)

Date: 2026-07-22
Strategy used: `DryRunEMACross` (EMA20/EMA50 crossover, BTC-USD, Kraken Pro Futures, 1h, market orders, fixed size). Deliberately un-tuned — performance numbers below are noise and irrelevant. This document validates **mechanics only**.

**This supersedes the original dry run** (preserved at `reports/DRYRUN.v1-corrupted-data.md.bak`). That first run was executed on Kraken Pro Futures candle data that was later discovered to be ~59% synthetically corrupted (see `reports/ZERO-VOLUME-DIAGNOSIS.md` and `reports/KRAKEN_DRIVER_BUG_REPORT.md` for the full root-cause investigation and fix). BTC-USD, ETH-USD, and SOL-USD have since been wiped and re-imported with a fixed driver; this run repeats the exact same checklist on that clean data.

---

## 1. Data availability

BTC-USD, ETH-USD, SOL-USD already cover the full available history (2022-04-01 → today) from the post-fix re-import — no fresh import was needed for this run.

| Symbol | First candle (1m, UTC) | Last candle (1m, UTC) | Usable history |
|---|---|---|---|
| BTC-USD | 2022-04-01 00:00 | 2026-07-22 11:58 | ~4.31 years |
| ETH-USD | 2022-04-01 00:00 | 2026-07-22 13:36 | ~4.31 years |
| SOL-USD | 2022-04-01 00:00 | 2026-07-22 14:56 | ~4.31 years |
| XRP-USD | 2023-01-01 00:00 | 2024-11-01 03:19 (partial, import was cancelled) | **out of scope — see note below** |

BTC-USD 1h aggregate: **37,764 candles** (2022-04-01 00:00 → 2026-07-22 11:00).

**XRP-USD note:** dropped from the research pool during the zero-volume investigation (unrelated driver mapping/history-maturity concern), its import was deliberately cancelled, and its existing partial data was left untouched (out of scope, not re-verified against the driver fix). Do not use it.

### Gap scan (BTC-USD, full history) — post-fix

- **Timestamp continuity: perfect**, as before.
- **1-minute flat candles:** 321,588 of 2,265,839 (14.2%) — normal, isolated single-minute gaps, not corruption.
- **1-hour fully zero-volume periods: 16 of 37,764 (0.04%)** — down from **59.1%** in the original run. Longest streak: 6 hours (2025-11-01 16:00→21:00). Every multi-hour streak across BTC, ETH, and SOL was individually cross-checked against Kraken's live API and confirmed genuine (real, isolated thin-liquidity/platform events — not synthetic fill). Full detail in `ZERO-VOLUME-DIAGNOSIS.md` Step 5.
- **This is the headline result of the whole remediation effort**: same symbol, same history, ~1500x fewer corrupted hours.

---

## 2. Backtest mechanics

One-year backtest, BTC-USD, 1h, 2023-01-01 → 2024-01-01, on clean data.

- **Execution time: 0.75 seconds.**
- Trades: 103 (identical to the pre-fix run for this exact window) | Sharpe: 0.791 | Max drawdown: -32.87% | Net profit: 29.9%
- Fees confirmed active and material: total fees $1,281.07 vs. net profit $2,990.32 (gross profit $19,958.62, gross loss -$16,968.30) — unchanged from before, confirming the fee model itself was never affected by the candle bug.
- Fee/slippage caveats from the original dry run still apply unchanged: Jesse's exchange config has one flat fee rate (no maker/taker split — fine here since this strategy is 100% market orders, but a gap for future limit-order strategies), and there is no configurable slippage parameter anywhere in Jesse (orders fill at the next candle's open, no separate stochastic slippage model).

---

## 3. Walk-forward mechanics

Same fold boundaries as the original run (real first-candle date 2022-04-01 matches the main prompt's assumption; Fold 1's IS start pushed to 2022-04-25 to leave room for the 210-candle warm-up buffer, per the fix learned in the original dry run):

| Fold | IS window | OOS window |
|---|---|---|
| 1 | 2022-04-25 → 2023-10-31 | 2023-11-01 → 2024-04-30 |
| 2 | 2022-10-01 → 2024-04-30 | 2024-05-01 → 2024-10-31 |
| 3 | 2023-04-01 → 2024-10-31 | 2024-11-01 → 2025-04-30 |

All 6 backtests completed without errors, in 0.47–1.52 seconds each:

| Session | Trades | Sharpe | Max DD | vs. pre-fix run |
|---|---|---|---|---|
| Fold1-IS | 164 | 0.167 | -46.24% | **identical** (164 / 0.167 / -46.24%) |
| Fold1-OOS | 84 | -0.246 | -23.96% | **changed** (was 52 / 2.54 / -14.56%) |
| Fold2-IS | 268 | 0.328 | -49.20% | **changed** (was 164 / 1.24 / -32.85%) |
| Fold2-OOS | 42 | 1.177 | -23.15% | **identical** (was 42 / 1.18 / -23.15%) |
| Fold3-IS | 155 | 1.227 | -23.96% | **identical** (was 155 / 1.23 / -23.96%) |
| Fold3-OOS | 86 | -0.869 | -46.00% | **changed** (was 45 / 1.55 / -18.96%) |

**This table is the concrete, quantified proof of why fixing the data mattered.** Half the folds (1-OOS, 2-IS, 3-OOS) produced materially different trade counts and Sharpe ratios once the synthetic zero-volume corruption was removed — including sign flips (Fold1-OOS and Fold3-OOS went from strongly positive Sharpe to negative). The other half happened to land in windows/trajectories where this particular slow trend-following signal was insensitive to the corruption and produced identical results either way. **A real research run on the old data would have scored some folds completely wrong**, which is exactly the failure mode the whole remediation was worried about. As always, the absolute numbers here are noise (untuned strategy) — only the mechanics (all 6 complete, inside available history, no errors) and the before/after delta matter for this dry run.

---

## 4. Monte Carlo mechanics

Ran on the Fold2-OOS backtest (BTC-USD, 2024-05-01 → 2024-10-31, 42 trades — a window that happened to be unaffected by the corruption, so these numbers match the original run).

- **Total wall time: ~45 seconds** for trade-shuffle (200/200) + candle-based (199/200) combined. Consistent with the original run — not a bottleneck.
- Trade-shuffle: original Sharpe 1.138 vs. median 1.122 (worst_5: 1.026, best_5: 1.205) — sits almost exactly on the median.
- Candle-based: original Sharpe 1.138 vs. median 1.430 (worst_5: -0.796, best_5: 3.629) — below median, well inside the band.
- Same minor finding as before: 1 of 200 candle-based scenarios didn't complete (199/200) — not blocking, but automation should check `completed_scenarios == num_scenarios`.

---

## 5. Correlation mechanics

Same method as the original run (daily returns aren't exposed directly by any MCP tool — derived from the `trades` table: each trade's PNL allocated to its close date, divided by starting balance, zero-filled on no-trade days).

Ran BTC-USD and ETH-USD, identical `DryRunEMACross` parameters, identical window (2024-05-01 → 2024-10-31, 42 trades each — the same window used in the Monte Carlo check above, which was unaffected by the corruption).

**Result: pairwise correlation of daily returns = 0.2634** — identical to the original (dirty-data) run, consistent with this window's trade sequence being unchanged by the fix.

---

## 6. Reporting & state mechanics

- `reports/` folder already existed; this file replaces the original `DRYRUN.md` (backed up at `DRYRUN.v1-corrupted-data.md.bak`).
- `STATE.md` and `REJECTED.md` already existed with the correct placeholder structure from the first run; `STATE.md` has been updated to clear the now-resolved data-quality blocker and reflect the current, clean state (see file).

---

## GO / NO-GO Verdict

**GO — all 6 steps pass on clean data, the pipeline is ready for the real research run on BTC-USD, ETH-USD, SOL-USD.**

Everything flagged as a blocker in the original dry run is now resolved:
1. ~~Zero-volume data corruption~~ — **fixed and validated**: 59.1% → 0.04-0.19% dead-hour rate across BTC/ETH/SOL, all remaining streaks individually confirmed genuine against Kraken's live API. Bug report prepared for upstream (`KRAKEN_DRIVER_BUG_REPORT.md`).
2. Fold 1 IS warm-up-buffer failure — known, worked around (start IS windows ~3 weeks after the raw first-candle date).
3. `get_existing_candles` / `get_candles` MCP tool limitations — still present, still worked around via direct Postgres queries; not a blocker since the workaround is established and documented.
4. Parallel-import throttling — confirmed multiple times now; sequential-only import is the established procedure.
5. Single flat fee rate (no maker/taker split) and no configurable slippage — still a gap for future limit-order strategies, not a blocker for this dry run's all-market-order test strategy. Worth deciding on a mitigation before strategies that rely on limit-order maker fees are scored.

No new blockers found in this re-run. Execution speed remains excellent (sub-second to ~1.5s backtests, ~45s Monte Carlo) and will not bottleneck a hundreds-of-candidates research run.
