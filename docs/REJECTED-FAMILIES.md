# REJECTED — Failed Candidates Log

> One line per failed candidate: name, symbol, timeframe, funnel stage reached, which criterion killed it. Never re-tune a candidate that failed here on the same idea — go back to in-sample research with something materially different.

<!-- Format:
- YYYY-MM-DD — StrategyName — SYMBOL — timeframe — Stage N (0/1/2/3) — killed by: <criterion>
-->

- 2026-07-23 — MeanRevRsi (RSI oversold/overbought reversion) — BTC-USD — 30m — Stage 0 — killed by: RST p=1.0000 (indistinguishable from random entries), annualized -0.07%. Naked RSI reversion with no trend/regime filter, in a mostly-trending market.
- 2026-07-23 — MeanRevBband (Bollinger Band touch reversion) — ETH-USD — 30m — Stage 0 — killed by: RST p=1.0000, annualized -0.28%. Same failure mode as MeanRevRsi.
- 2026-07-23 — MeanRevZscore (z-score extreme reversion) — SOL-USD — 1h — Stage 0 — killed by: RST p=1.0000, annualized -0.58%. Same failure mode.
- 2026-07-23 — MomentumWillrExtreme (Williams %R extreme reversal) — ETH-USD — 30m — Stage 0 — killed by: RST p=1.0000, annualized -0.35%. Same reversion-without-regime-filter failure mode.
- 2026-07-23 — BreakoutDonchian (Donchian(30) + 4h SMA trend + ATR>SMA(ATR) volatility filter, as specified by a pre-existing stub found in the repo) — BTC-USD — 1h+4h anchor — Stage 0 — killed by: 0 closed trades over 2022-05-20→2025-10-31 (~3.5 years). The 3-way filter combination never triggers; RST degenerated to p=1.0/0.00 return with no observations to test. Entry logic needs loosening (drop one filter, or widen thresholds) before it's worth retrying as a different candidate.

**Pattern noted for future waves:** all 4 pure mean-reversion/reversion-style candidates in wave 1 failed Stage 0 uniformly. Naked oversold/overbought or z-score entries don't have edge on BTC/ETH/SOL 2022-2025 without a trend/regime filter (e.g., only mean-revert when ADX is low). Any future mean-reversion candidate should add that filter from the start rather than repeating this exact failure.

- 2026-07-23 — BreakoutAtrExpansion (ATR-expansion momentum breakout) — SOL-USD — 30m — Stage 1 — killed by: clearly poor Sharpe (-0.799), absurd drawdown (-65.35%), net -58.83% on Fold 1 IS (2022-04-25→2023-10-31). Passed Stage 0 (p=0.0000) but the entry timing edge doesn't translate into a viable exit/risk setup at these ATR multiples.
- 2026-07-23 — VolBbandSqueeze (Bollinger squeeze breakout) — ETH-USD — 1h — Stage 1 — killed by: too few trades (16 over the 18-month IS window, ~41 over the full 3.5yr history), negative Sharpe (-0.445). Squeeze condition (BB width at its own 50-bar rolling minimum) is too rare to be statistically usable even though Stage 0 technically passed (p=0.0000 on a near-zero observed effect).

### Wave 1 — Stage 2 (full 4-fold walk-forward) rejections, 2026-07-23

All 7 candidates that passed Stage 0+1 were walk-forward tested on the real 4-fold protocol (Fold1 OOS 2023-11→2024-04, Fold2 OOS 2024-05→2024-10, Fold3 OOS 2024-11→2025-04, Fold4 OOS 2025-05→2025-10). **None met the acceptance bar (OOS Sharpe > 1.5 in ≥3 of 4 folds).** Per-fold OOS Sharpe / max DD:

| Strategy | Symbol/TF | F1-OOS | F2-OOS | F3-OOS | F4-OOS | Folds >1.5 |
|---|---|---|---|---|---|---|
| TrendEmaCross | BTC 1h | 0.26 / -21% | 0.05 / -21% | 0.17 / -23% | 0.02 / -21% | 0/4 |
| SuperTrend | ETH 1h | -0.04 / -14% | -0.83 / -15% | -2.65 / -29% | 1.35 / -15% | 0/4 |
| TrendAdxDi | SOL 1h | -1.42 / -23% | -0.42 / -15% | 0.24 / -13% | 1.23 / -11% | 0/4 |
| BreakoutKeltner | ETH 1h | 0.67 / -10% | **1.64** / -11% | 0.76 / -8% | **1.93** / -13% | 2/4 (closest) |
| MomentumMacdZero | BTC 1h | -0.62 / -19% | 1.39 / -13% | -1.54 / **-44%** | -3.75 / **-47%** | 0/4, also breaches max-DD<30% on 2 folds |
| MomentumRsi50Cross | SOL 1h | -0.23 / -16% | -1.23 / -30% | 1.05 / -12% | 1.05 / -14% | 0/4 |
| TrendEmaAnchor4h | BTC 1h+4h | 0.18 / -21% | -0.03 / -17% | 0.09 / -21% | 0.04 / -20% | 0/4 |

- 2026-07-23 — TrendEmaCross — BTC-USD — 1h — Stage 2 — killed by: OOS Sharpe never exceeds 0.26 in any of 4 folds (bar is 1.5 in ≥3/4). Plain EMA crossover has no edge on hourly BTC once walk-forward tested out-of-sample.
- 2026-07-23 — SuperTrend — ETH-USD — 1h — Stage 2 — killed by: 0/4 folds >1.5, Fold3-OOS Sharpe -2.65 with -29% DD (near the DD limit on top of a bad Sharpe).
- 2026-07-23 — TrendAdxDi — SOL-USD — 1h — Stage 2 — killed by: 0/4 folds >1.5; only becomes OOS-positive in the two most recent folds, no consistency across regimes.
- 2026-07-23 — MomentumMacdZero — BTC-USD — 1h — Stage 2 — killed by: 0/4 folds >1.5 AND breaches the max-DD<30%-on-every-OOS-window rule on two folds (-44%, -47%). The exit (wait for opposite MACD-histogram cross, no trailing stop) lets losers run unchecked — a structural risk-management flaw, not just a weak signal.
- 2026-07-23 — MomentumRsi50Cross — SOL-USD — 1h — Stage 2 — killed by: 0/4 folds >1.5, and Fold2-OOS DD -29.70% is right at the limit.
- 2026-07-23 — TrendEmaAnchor4h — BTC-USD — 1h+4h anchor — Stage 2 — killed by: 0/4 folds >1.5. The 4h anchor filter did not meaningfully improve on plain TrendEmaCross (compare F1-4 OOS Sharpe: both hover near 0) — the anchor-timeframe idea itself isn't validated by this attempt, only this specific implementation of it.
- 2026-07-23 — BreakoutKeltner — ETH-USD — 1h — Stage 2 — killed by: only 2/4 folds >1.5 (need ≥3). **Closest miss of wave 1** — consistently positive, never catastrophic (worst DD -13%), Sharpe just short of the bar in Folds 1 and 3. Worth a materially-different follow-up (e.g. tighter/trailing exit instead of exit-at-midline) as a wave 2 candidate — not a re-tune of this exact one on OOS data, a fresh Stage-0 candidate with a different risk-management mechanism.

**Wave 1 verdict:** 0 accepted. Consistent pattern: naked trend-following and momentum signals on 1h don't clear a 1.5 OOS Sharpe bar across BTC/ETH/SOL without either a regime filter or tighter risk management. Wave 2 should diversify mechanism (grid/multi-entry, regime-filtered mean reversion, short-only) rather than more parameter variants of the same four families already tried.

### Wave 2 — Stage 0 rejections, 2026-07-23

- 2026-07-23 — GridMeanReversion (z-score-triggered multi-level limit-order grid, mean reversion to SMA) — BTC-USD — 1h — Stage 0 — killed by: RST p=1.0000, annualized -0.26%. The grid/multi-entry mechanism itself works correctly (192 trades in a pre-check, no errors), but the underlying entry timing (z-score extreme) still has no edge — same root cause as wave 1's mean-reversion failures, mechanism doesn't fix a signal problem.
- 2026-07-23 — RegimeFilteredMeanRev (RSI reversion gated by ADX<20, ranging-regime only) — ETH-USD — 30m — Stage 0 — killed by: RST p=1.0000, ~0% annualized. **Important negative result: adding a trend/regime filter to naked RSI reversion did NOT fix the Stage-0 failure**, contradicting the hypothesis noted after wave 1. Mean reversion (RSI, Bollinger, z-score, now regime-filtered RSI too) has failed Stage 0 in every single form tried on BTC/ETH/SOL 2022-2025 (5 attempts, 5 failures). Treat naked oscillator-based mean reversion as a dead family for this pool/period — a future attempt would need a genuinely different trigger (e.g. mean reversion of the SPREAD between two correlated assets, not of price vs. its own average) rather than another regime filter on the same RSI/BB/z-score idea.

### Wave 2 — Stage 1 rejections, 2026-07-23

Bug found and fixed in passing (not a signal/parameter change, so no protocol issue): `DonchianBreakoutSimple`'s `should_long`/`should_short` could both be true simultaneously when the Donchian channel degenerates to a flat line (upperband==lowerband), which Jesse correctly rejects as an invalid state. Fixed with an `upperband > lowerband` guard on both conditions, then re-ran.

- 2026-07-23 — DonchianBreakoutSimple — BTC-USD — 30m — Stage 1 — killed by: clearly poor Sharpe (-1.22), net -13.79% on Fold1 IS. The unfiltered breakout family (this + wave 1's over-filtered BreakoutDonchian) is now 0-for-2; not worth a third attempt without a fundamentally different trigger.
- 2026-07-23 — MomentumMacdTrail — SOL-USD — 1h — Stage 1 — killed by: absurd drawdown (-50.71%) on Fold1 IS — worse than wave 1's MomentumMacdZero this was meant to fix (that one hit -44%/-47% only in 2 of 4 OOS folds; this hits -50% already in-sample). The ATR trailing stop didn't fix the underlying issue: MACD histogram entries on SOL are simply too whippy/reversal-prone for this exit style. MACD-histogram-based momentum entries are now 0-for-2 across both symbols/exit-styles tried.

**Survivors to Stage 2:** KeltnerBreakoutTrail (ETH-USD 1h, Sharpe -0.07/DD -28% on Fold1 IS — weak but not clearly poor, advancing per the letter of the Stage 1 bar even though it underperforms its wave-1 sibling BreakoutKeltner on this identical window) and ShortOnlyBreakdown (SOL-USD 1h, Sharpe 0.33/DD -13%/38 trades, net +4.69% on Fold1 IS).

### Wave 2 — Stage 2 (full 4-fold walk-forward) rejections, 2026-07-23

| Strategy | F1-OOS | F2-OOS | F3-OOS | F4-OOS | Folds >1.5 |
|---|---|---|---|---|---|
| KeltnerBreakoutTrail | -0.75 / -20% | **2.45** / -10% | 1.22 / -10% | 1.09 / -21% | 1/4 |
| ShortOnlyBreakdown | -1.42 (1 trade) | -1.97 (4 trades) | **2.02** (3 trades) | -2.47 (3 trades) | 1/4, and only 11 total OOS trades |

- 2026-07-23 — KeltnerBreakoutTrail — ETH-USD — 1h — Stage 2 — killed by: only 1/4 folds >1.5 (need ≥3). **Notable: Fold2-OOS hit Sharpe 2.45** — the ATR-trailing-stop exit variant has real upside in trending regimes but is inconsistent across the other 3 folds (choppy periods hurt it, e.g. Fold3-IS DD -38%). Compare to wave 1's exit-at-midline BreakoutKeltner sibling (2/4 folds >1.5, more consistent but lower ceiling) — the Keltner breakout ENTRY looks like the strongest signal found across both waves; the EXIT mechanism is the open question, not the entry.
- 2026-07-23 — ShortOnlyBreakdown — SOL-USD — 1h — Stage 2 — killed by: only 1/4 folds >1.5 AND a combined 11 trades across all 4 OOS windows (need ≥100 total) — the Donchian-low + below-SMA(50) breakdown condition is simply too rare on SOL to be statistically usable, regardless of the Sharpe swings (which are themselves noise on 1-4 trades per fold).

**Wave 2 verdict:** 0 accepted, same as wave 1 — 0/10 total after 2 waves, 9 distinct candidates fully walk-forward tested. **Key finding carried into wave 3: Keltner-channel breakout is the only entry family showing real signal** (2/4 and 1/4-with-a-2.45-fold across its two exit variants) — wave 3 should iterate on this family's exit/filter mechanism and try it on the untested symbol (SOL) and a volatility regime filter, rather than opening new unrelated families. Mean reversion (5/5 Stage-0 failures) and MACD momentum (0/2 Stage-2, both blew up on drawdown) are dead ends for this pool — do not retry either without a fundamentally different trigger.

### Wave 3 — Stage 2 rejections, 2026-07-23

All 4 candidates passed Stage 0 and Stage 1 (no clear failures — see STATE.md history). Full 4-fold walk-forward:

| Strategy | F1-OOS | F2-OOS | F3-OOS | F4-OOS | Folds >1.5 |
|---|---|---|---|---|---|
| BreakoutKeltner BTC-USD (new symbol) | -0.43 | -0.42 | -1.07 | -1.19 | 0/4 |
| BreakoutKeltner SOL-USD (new symbol) | 0.93 | -0.93 | **1.61** | 0.65 | 1/4 |
| KeltnerBreakoutHybrid (partial-close exit) ETH-USD | -0.74 | **1.52** | 1.22 | 1.09 | 1/4 |
| KeltnerBreakoutVolFilter (ATR>SMA(ATR) filter) ETH-USD | 0.48 | **1.92** | 1.09 | **1.97** | 2/4, **closest yet, never catastrophic (worst OOS DD -13.4%, every OOS Sharpe positive)** |

- 2026-07-23 — BreakoutKeltner — BTC-USD — 1h — Stage 2 — killed by: 0/4 folds >1.5. Confirms BTC is a weak symbol for this entry (also true in wave 1's TrendEmaCross/MomentumMacdZero — BTC-USD 1h consistently underperforms ETH/SOL across every family tried in this research run).
- 2026-07-23 — BreakoutKeltner — SOL-USD — 1h — Stage 2 — killed by: only 1/4 folds >1.5, despite the best raw Stage-1 IS Sharpe (0.84) of any wave-3 candidate — high fold-to-fold variance (0.93 → -0.93 → 1.61 → 0.65) means the edge isn't stable.
- 2026-07-23 — KeltnerBreakoutHybrid — ETH-USD — 1h — Stage 2 — killed by: only 1/4 folds >1.5 (Fold2 barely clears at 1.52). The partial-close-at-midline/trail-remainder exit underperforms the simpler `KeltnerBreakoutVolFilter` exit below.
- 2026-07-23 — KeltnerBreakoutVolFilter — ETH-USD — 1h — Stage 2 — killed by: only 2/4 folds >1.5 (need ≥3). **Best result across all 24 candidates tried in 3 waves** — no catastrophic fold, every OOS Sharpe positive, max OOS DD -13.4%. Long-side win rate (13-50%) consistently beats short-side (23-27%) across all 4 folds — worth a long-only variant and a per-symbol retry (SOL showed the strongest raw entry) before concluding the family is exhausted.

**Wave 3 verdict:** 0 accepted. 24 distinct strategy/symbol candidates now created across 3 waves; 13 fully walk-forward tested to Stage 2 (7 wave 1 + 2 wave 2 + 4 wave 3), remainder killed earlier in the funnel. **Escalation checkpoint reached** — logged in STATE.md. One final, narrowly-targeted wave 4 (2 candidates: long-only Keltner-vol-filter, and Keltner-vol-filter on SOL) is being run before considering whether to stop and report to Tom that the 1.5-OOS-Sharpe-in-3/4-folds bar may be unreachable for this symbol/timeframe pool with the mechanisms tried so far.

### Wave 4 — Stage 2 rejections, 2026-07-23 (final wave before escalation)

Two narrowly-targeted refinements of wave 3's best candidate (`KeltnerBreakoutVolFilter`, 2/4 OOS folds >1.5), based on its own data: longs beat shorts on every fold, and SOL showed the strongest raw entry signal of the three symbols tested.

| Strategy | F1-OOS | F2-OOS | F3-OOS | F4-OOS | Folds >1.5 | Total OOS trades |
|---|---|---|---|---|---|---|
| KeltnerLongOnlyVolFilter (long-only, ETH-USD) | 0.82 | 1.06 | 0.41 | **3.00** | 1/4 | 181 |
| KeltnerVolFilterSOL (both sides, SOL-USD) | 0.96 | -0.70 | **1.78** | 0.79 | 1/4 | 324 |

- 2026-07-23 — KeltnerLongOnlyVolFilter — ETH-USD — 1h — Stage 2 — killed by: only 1/4 folds >1.5 — **worse** than the both-sides wave-3 parent (2/4), despite the long-side-outperforms-short-side finding that motivated it. Dropping shorts removed some losses but also removed enough winning trades that overall fold consistency got worse, not better. Never catastrophic (max OOS DD -21%, one exceptional fold at 3.00).
- 2026-07-23 — KeltnerVolFilterSOL — SOL-USD — 1h — Stage 2 — killed by: only 1/4 folds >1.5 — also **worse** than the ETH parent (2/4) despite SOL's stronger raw Stage-1 signal; Fold2-OOS actively negative (-0.70). Confirms wave 3's BreakoutKeltner-SOL finding: SOL's Keltner-breakout edge is real but has higher fold-to-fold variance than ETH's, which hurts the ≥3/4-folds consistency requirement specifically (even though average/best-case performance can look strong).

**Wave 4 verdict — RESEARCH HALTED, ESCALATING TO TOM.** 4 full research waves, 26 distinct strategy/symbol candidates created, 15 fully walk-forward tested to Stage 2 (~91 individual walk-forward backtests just in Stage 2 across all 4 waves, plus ~30 Stage 0 significance tests and ~25 Stage 1 screens — roughly 150 total backtests/tests run). Every mechanism family in the original brief has been tried: trend-following (EMA cross, SuperTrend, ADX+DI, 4h-anchored), mean reversion (RSI, Bollinger, z-score, ADX-regime-filtered, grid/multi-entry) — 0-for-6 at Stage 0, momentum (MACD histogram, RSI-50-cross, Williams %R) — 0-for-6 at Stage 0/2, breakout (Donchian filtered and unfiltered, Keltner, ATR-expansion), volatility (Bollinger squeeze), and short-only (SOL breakdown). **Keltner-channel breakout is the only family with genuine, non-random, non-catastrophic signal** (Stage 0 p=0.0000 in every variant tried, OOS Sharpe never deeply negative, OOS drawdown always well under the 30% limit) — but across 6 variants (2 exit styles × wave 1, exit-at-midline/ATR-trail/partial-close/vol-filter/long-only/SOL-symbol × waves 1-4) it consistently caps at 1-2 of 4 OOS folds clearing Sharpe 1.5, never reaching the required 3/4. This looks like a genuine ceiling, not an unexplored corner — see the message to Tom for the full recommendation.
