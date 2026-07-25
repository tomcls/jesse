# Research Run #1 — Final Summary

**Date:** 2026-07-23
**Result:** 0 / 10 strategies accepted. Research halted per protocol, decision confirmed by Tom: accept this as the honest result rather than relax the acceptance bar or force a marginal candidate through. See `STATE.md` and `REJECTED.md` for full detail.

This is not a failure of the pipeline — the funnel worked exactly as designed. It correctly killed 26 candidates across every mechanism family in the brief, most of them cheaply at Stage 0/1, and refused to pass anything through on a technicality. Per the roadmap's own stated philosophy: *"the project's success metric ≠ number of strategies found; it's the reliability of what passes the filter."* Zero strategies that don't hold up is a better outcome than ten that do not survive live trading.

---

## What was tried (4 waves, 26 candidates, ~150 backtests/tests)

| Family | Variants tried | Outcome |
|---|---|---|
| Trend-following | EMA cross, SuperTrend, ADX+DI, EMA + 4h anchor filter | 0/7 passed Stage 2 |
| Mean reversion | RSI, Bollinger touch, z-score, grid multi-entry, ADX-regime-filtered RSI | **Dead — 0/5 failed at Stage 0** (indistinguishable from random entries in every form) |
| Momentum | MACD histogram (exit-on-cross and ATR-trail variants), RSI-50 cross, Williams %R extreme | 0/6, two variants breached the 30%-max-DD OOS rule from having no trailing stop |
| Breakout — Donchian | Filtered (trend+volatility gate, from a pre-existing repo stub) and unfiltered | 0/2 — the filtered version never triggered a single trade in 3.5 years; the unfiltered version had no edge |
| Breakout — Keltner | Exit-at-midline, ATR-trail, partial-close hybrid, volatility-filtered, long-only, retried on SOL/BTC | **The only family with real signal** — see below |
| Breakout — volatility expansion | ATR-expansion momentum trigger | Failed Stage 1 (Sharpe -0.80, DD -65%) |
| Volatility squeeze | Bollinger Band width squeeze breakout | Failed Stage 1 (too few trades) |
| Short-only | Donchian-low + below-SMA(50) breakdown on SOL | Failed Stage 2 (too few trades: 11 total OOS) |

## The one real finding: Keltner-channel breakout

Every Keltner-breakout variant passed Stage 0 with `p_value = 0.0000` — a statistically real, non-random entry signal, the only family in the entire run to show this consistently. Across every OOS fold in every variant, the strategy was never catastrophic: Sharpe was rarely deeply negative, and max drawdown never approached the 30% limit.

But across 6 distinct variants, it never broke a ceiling of **2 out of 4 OOS folds clearing Sharpe > 1.5** (the bar requires ≥3/4):

| Variant | Symbol | Exit style | Folds >1.5 |
|---|---|---|---|
| BreakoutKeltner (wave 1) | ETH-USD | Exit-at-midline | 2/4 |
| KeltnerBreakoutTrail (wave 2) | ETH-USD | ATR trailing stop | 1/4 (one fold hit 2.45) |
| KeltnerBreakoutHybrid (wave 3) | ETH-USD | Partial-close + trail | 1/4 |
| **KeltnerBreakoutVolFilter (wave 3)** | **ETH-USD** | **Exit-at-midline + ATR>SMA(ATR) volatility gate** | **2/4 — best result of the entire run** |
| KeltnerLongOnlyVolFilter (wave 4) | ETH-USD | Same as above, long-only | 1/4 (one fold hit 3.00) |
| KeltnerVolFilterSOL (wave 4) | SOL-USD | Same as above | 1/4 (one fold hit 1.78) |
| BreakoutKeltner (wave 3) | SOL-USD | Exit-at-midline | 1/4 |
| BreakoutKeltner (wave 3) | BTC-USD | Exit-at-midline | 0/4 — BTC consistently the weakest symbol across every family tried |

**Best candidate: `KeltnerBreakoutVolFilter` on ETH-USD, 1h.** Code preserved at `strategies/KeltnerBreakoutVolFilter/__init__.py`.

Logic: enter long on a close above the Keltner channel upper band, short on a close below the lower band, but only when ATR is above its own 20-period rolling average (a volatility-expansion regime gate that filters out the choppy, low-volatility stretches that hurt the unfiltered version). Exit when price crosses back through the channel midline. Position sized via `risk_to_qty` at the strategy's `risk_percent` hyperparameter, stop-loss at `entry ± atr_mult × ATR`.

Fold-by-fold (2022-04-25 → 2025-10-31 walk-forward, real Kraken Pro Futures data, leverage 3x, 0.05% taker fee):

| Fold | IS Sharpe | OOS Sharpe | OOS max DD |
|---|---|---|---|
| 1 | — (Fold1 IS not separately re-run for this variant; Stage 1 screen used Fold1 IS window, Sharpe 0.245) | 0.48 | -12.7% |
| 2 | -0.12 | **1.92** | -10.3% |
| 3 | -0.004 | 1.09 | -9.9% |
| 4 | 0.74 | **1.97** | -13.4% |

## Why this looks like a real ceiling, not an unexplored corner

1. **Consistent across 6 variants.** Changing the exit mechanism (midline / ATR-trail / partial-close / vol-filter), the side (both / long-only), and the symbol (ETH / SOL / BTC) all produced the same 1-2/4 pattern. If this were a tuning problem, at least one combination should have broken through.
2. **The signal is genuine, not noise.** Stage 0 rule-significance p=0.0000 every time (2000 random-entry simulations), and Stage 2 never produced a catastrophic OOS fold — this isn't a strategy getting lucky and then failing; it's a real, moderate edge that just doesn't clear the specific 1.5-Sharpe-in-3/4-folds bar consistently.
3. **The fold that fails is usually a different one each time** (Fold1 for wave 3's ETH variant, Fold2 for SOL, Fold1+Fold3 for the long-only variant) — suggesting genuine regime-dependency (the entry works in trending/volatile stretches and doesn't in choppy ones) rather than a single bad time window skewing everything.
4. **Mean reversion is unambiguously dead** for this pool (5/5 Stage-0 failures, every plausible oscillator/z-score/grid variant, with and without regime filters) — that's not a maybe, it's now well-established for BTC/ETH/SOL 2022-2025 on 30m/1h.

## What's left unexplored (for a future session, if research resumes)

- **30m timeframe was never tried for Keltner breakout** — every variant was 1h. Worth a systematic pass given the entry signal's proven realness.
- **Hyperparameter optimization within Stage 2's IS windows** — every variant used the same default hyperparameters throughout (period=20, mult=2.0, atr_mult=2.0, etc.). Jesse's built-in optimizer (`run_optimization`, per-fold, IS-only) was never invoked. This is the most promising immediate next step: the entry/filter mechanism is validated, only the exact parameters are unoptimized.
- **ETH/BTC or ETH/SOL pairs trading / stat-arb** — never attempted; a genuinely different mechanism from everything tried.
- **Asymmetric long/short Keltner parameters** (different `period`/`mult` per side) — only symmetric versions were tried.
- **Combining the volatility filter with a longer-term trend filter** (e.g., only trade in the direction of a 4h/1D trend) — untested combination.

## Files

- `STATE.md` — current status (halted, 0/10, decision recorded)
- `REJECTED.md` — full rejection log with per-fold numbers for all 26 candidates
- `reports/DRYRUN.md`, `reports/ZERO-VOLUME-DIAGNOSIS.md`, `reports/KRAKEN_DRIVER_BUG_REPORT.md`, `reports/MCP_CONFIG_UPDATE_BUG_REPORT.md` — pipeline validation and infrastructure bug reports from before this research run started
- `strategies/KeltnerBreakoutVolFilter/`, `strategies/KeltnerBreakoutTrail/`, `strategies/KeltnerBreakoutHybrid/`, `strategies/KeltnerLongOnlyVolFilter/`, `strategies/KeltnerVolFilterSOL/`, `strategies/BreakoutKeltner/` — all 6 Keltner-breakout variants, code preserved for future refinement
