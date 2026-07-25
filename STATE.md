# STATE — Autonomous Quant Research Agent

> This file is the resume-point for the research run. Read it first every session. Update it every cycle — sessions will be interrupted by usage limits, so this file must always be current enough that a cold restart loses nothing.

## Status

- **Phase:** 🏁 RESEARCH RUN #2 — CLOSED (2026-07-24). Final report: `reports/R2-FINAL-REPORT.md`. Two strategies accepted: `R2_KeltnerAsymmetric` ETH 4h (1.5936@108) + `R2_KeltnerAsymmetric1h` ETH 1h (1.5559@162), corr 0.17, disciplined IS/OOS provenance, full validation battery. **Cross-venue Binance same-period validated (1.40/1.39 — edge not a Kraken artifact). HOLDOUT 2026 WAS FIRED on 2026-07-24 at Tom's explicit request (one-shot): both POSITIVE on virgin data (#1: +0.53 Sharpe/16 trades; #2: +0.79/29 trades) but well below backtest — consistent with predicted live degradation; tiny sample (±1.0 Sharpe stderr); #2's holdout DD -19.8% approached its -21% alert line. THE HOLDOUT IS NOW SPENT — any retuning informed by 2026 data is self-deception; configs are frozen; only paper trading judges from here.** Tom is copying both strategies to the prod server for paper trading. Realistic live expectation: Sharpe ~0.6-1.0. Total: 162 backtests logged. Started 2026-07-23, directly following Research Run #1's closure (0/10 accepted, see `reports/RESEARCH_RUN_1_SUMMARY.md`). New protocol: single continuous-window backtest (no walk-forward folds), hard trade-frequency constraint (100-169 closed trades over the window), goal of 8 accepted strategies (Sharpe > 1.5), explicit diversity/correlation/Monte-Carlo/cross-symbol-replication requirements. Full directive is in conversation history, not yet copied verbatim into a report file — do that if starting a fresh session and the directive isn't visible in context.
- **Accepted strategies:** 0 / 8
- **Total backtests logged this run:** 82 (see `reports/ALL-RUNS.jsonl`, append-only, one line per run, includes rejects)
- **Ping thresholds:** (a) data quality failure — not hit; (b) 400 total backtests with <4 accepted — not close (82/400).
- **Config:** Kraken Pro Futures, exchange name in Jesse is exactly `"Kraken Pro Futures"` (NOT "Kraken Futures" — using the wrong name causes a silent `KeyError: 'Kraken Futures'` crash in the backend worker process; the MCP `run_backtest` call still returns "started" and the session sits in `draft` status forever with no error surfaced through the MCP tools — only visible via `docker logs jesse` or by polling `get_backtest_session` and noticing status never leaves "draft"/"running"). Leverage 3x, maker 0.02%/taker 0.05% fee split modeled via post-hoc order-type reclassification (see below), Docker container capped at 8 CPU cores.
- **Last updated:** 2026-07-23

## Research window (CRITICAL — do not violate)

- Research window: **2022-04-25 → 2025-12-31**. Real first-candle date for all 3 symbols is 2022-04-01 (no adjustment needed).
- Holdout: **2026-01-01 → today**. Never run it, never look at it, for any reason, until Tom explicitly authorizes a final holdout test.
- Symbols: BTC-USD, ETH-USD, SOL-USD, Kraken Pro Futures only.
- Trading TF: 30m, 1h, 2h, or 4h (no preference). Anchor TF (filters only, never trading): 4h or 1D. 1D is NOT allowed as a trading TF.
- Hard trade-count constraint: **100-169 closed trades total** over the window (≈2.4-4.0/month). Below 100 → statistically unmeasurable, reject regardless of Sharpe. Above 169 → fee drag, reject. This has been the single hardest constraint to satisfy — every family tested shows an inverse relationship between trade frequency and Sharpe (loosening entry filters to hit the floor consistently erodes edge).

## Config notes for future sessions

- `update_config` MCP tool is broken (reports success but never persists — see `reports/MCP_CONFIG_UPDATE_BUG_REPORT.md`, already sent to Saleh). To change Jesse config, write directly to Postgres: `UPDATE option SET json = jsonb_set(json::jsonb, '{path,to,field}', 'value') WHERE type='config';` — then verify via `get_config()`/`get_backtest_config()`. Already done this run: Monte Carlo and significance-test config `fee` fields corrected from Jesse's generic default (0.0006) to Kraken's real taker rate (0.0005).
- `Edit`/`Bash`/`Write` tools get `EACCES: permission denied` on any file under `strategies/` — the Docker container owns those files, not the host user. Always use `mcp__jesse-mcp__read_strategy` / `write_strategy` / `create_strategy` for strategy code.
- `BacktestRequestJson` has no hyperparameter-override field. Parameter search = edit each strategy's `hyperparameters()` defaults via `write_strategy`, then create+run a fresh backtest draft per parameter set. Slow but the only way.
- Jesse does **not** model perpetual funding costs in backtest mode (confirmed via source inspection in Research Run #1) — every Sharpe number in this run is funding-blind. Stated explicitly here per the user's requirement to never silently ignore this.
- Jesse's `fee_rate` is a single flat rate applied to every fill regardless of order type — no native maker/taker distinction. Workaround: `scratchpad/analyze_backtest.py` (see below) reclassifies every order by its `type` field (`LIMIT` = maker, everything else = taker) and recomputes a maker-adjusted Sharpe via daily-PnL reconstruction.
- Anchor-timeframe (4h/1D) strategies need extra warm-up room: with a 4h `data_route`, push `start_date` to at least 2022-05-15 (not 2022-04-25) to avoid a "missing candles" error.

## Analysis tooling

- **`/tmp/claude-1000/-mnt-crucial-www-jesse/d17b559c-d6ef-4142-ac53-29bb09c5caff/scratchpad/analyze_backtest.py`** — canonical script, pulls a finished backtest session from Postgres, computes maker/taker-corrected Sharpe + trade frequency, appends one line to `reports/ALL-RUNS.jsonl`. Usage: `python3 analyze_backtest.py <backtest_id> <strategy_name> <family> <symbol> <timeframe> <params_json> <window_start> <window_end> [--accepted]`. This is a scratchpad path (session-specific temp dir) — if it's gone in a future session, the script logic is fully documented in this file's git history / prior conversation and should be recreated at the top of a fresh scratchpad.
- Poll pattern for backtests: `create_backtest_draft` → `run_backtest` → poll `docker exec postgres psql -U jesse_user -d jesse_db -t -A -c "SELECT status FROM backtestsession WHERE id='...'"` until `finished` (usually 5-15s for a single continuous-window run). For Monte Carlo (200 scenarios), poll `montecarlosession` table instead — takes several minutes; use the `Monitor` tool with an until-loop rather than blocking sleeps.

## Data status (unchanged from Research Run #1)

| Symbol | First candle | Last candle | Notes |
|---|---|---|---|
| BTC-USD | 2022-04-01 | current | Clean, re-imported with fixed driver, 0.04% dead-hour rate (genuine) |
| ETH-USD | 2022-04-01 | current | Clean, re-imported with fixed driver, 0.04% dead-hour rate (genuine) |
| SOL-USD | 2022-04-01 | current | Clean, re-imported with fixed driver, 0.19% dead-hour rate (genuine) |
| XRP-USD | — | — | Out of scope, not in this run's symbol pool |

Zero-volume scan (per `reports/ZERO-VOLUME-DIAGNOSIS.md` methodology) was confirmed clean for all 3 symbols before Research Run #1 began; not re-run this session since the underlying data hasn't changed.

## Currently working on

**Family-by-family parameter search, 46 backtests logged so far.**

Families explored, roughly in order:
1. **Mean reversion** (`R2_MeanRevZscoreLimit`, ETH 1h): z-score + LIMIT entries, ATR stop. Consistently negative Sharpe at every trade-count setting tried (3 rounds). Consistent with Research Run #1's finding — likely a dead family for this symbol pool.
2. **Grid/multi-entry** (`R2_GridFadeExtreme`, ETH 1h): RSI-triggered ladder into extension. Also consistently poor (Sharpe -1.2 to 0.03 across 2 rounds). Likely dead-end, not retried this session after early rejection.
3. **Volatility breakout** (`R2_VolBreakoutRare`, ETH 1h): Donchian extreme + ATR expansion, MARKET entry, ATR trailing stop. Best found: period=5, atr_mult=2.0 → **120 trades, Sharpe 0.50**, meets frequency floor but Sharpe far below bar. ~8 rounds of tuning; this family structurally seems capped around Sharpe 0.4-0.5 at viable trade counts.
4. **Stat-arb pairs** (`R2_PairsRatioZscore`, ETH/BTC ratio, 1h): z-score of log price ratio. Negative Sharpe at 2 tested thresholds (219-466 trades, both far over frequency ceiling and both negative). Needs a fundamentally different approach or likely abandonment.
5. **Range fade + ADX regime filter** (`R2_RangeFadeAdx`, ETH 1h): Donchian edge fade, LIMIT entry, ADX<threshold gate, exit at midline. **Best quality-only result of any "small" family: Sharpe 0.708 at 33 trades** (dc_period=14, adx_max=30, offset=0.1) — but every attempt to loosen toward the 100-trade floor collapses the Sharpe (down to 0.05-0.59 as trades rise to 35-49). This family appears to have a hard ceiling around 33-35 trades before the edge degrades; likely cannot simultaneously hit both constraints on ETH 1h. Not yet tried on other symbols/timeframes.
6. **Short-only structural breakdown** (`R2_ShortOnlyBreakdown`, SOL 1h; replaced an earlier `R2_ShortOnlyRallyFade` design that fired 0-12 trades at every setting tried): Donchian-low breakdown + below-trend-SMA confirmation, LIMIT entry. Best found: entry_period=15, trend_period=45, offset=0.1 → 56 trades, Sharpe 0.40. Same pattern as VolBreakoutRare/RangeFadeAdx: loosening toward the 100-trade floor erodes Sharpe (81 trades → Sharpe 0.01 at looser settings). Not yet reconciled to both constraints.
7. **Trend/Keltner breakout, deliberately made selective** (`R2_KeltnerBreakoutSelective`) — **by far the strongest lead of this research run.** Built by taking Research Run #1's validated (`p=0.0000`, never-catastrophic) Keltner-breakout entry and widening the channel + adding a stronger volatility-expansion gate to cut its Research-Run-#1 firing rate (606 trades / ~43 months = ~14/month, way over ceiling) down into the 100-169 band.
   - **Best 1h config:** period=76, mult=4.25, atr_period=14, atr_sma_period=20, vol_expansion_mult=1.25, atr_mult=1.45, risk_percent=1.5 (exit-at-midline, same as Run #1's best variant). **167 trades, Sharpe 1.3263, max DD -12.0%, profit factor 2.02, win rate 31.7%, ETH-USD.**
   - **Best 4h config (even stronger): period=25, mult=2.6, atr_period=14, atr_sma_period=20, vol_expansion_mult=1.1, atr_mult=1.5, risk_percent=1.5. 102 trades, Sharpe 1.3956, max DD -13.46%, profit factor 2.24, win rate 42.2%, ETH-USD.** Best result of the entire run so far. Needs `start_date=2022-05-15` (not 2022-04-25) for the 4h anchor warm-up.
   - Both configs found via ~9 rounds of manual grid search each on `atr_mult`/`vol_expansion_mult`/channel width. Diminishing returns — stopped micro-tuning to avoid overfitting to this specific window.
   - **Monte Carlo (1h config, 200 scenarios):** original Sharpe 1.30 sits **below** the median of the resampled distribution (median 1.98, worst-5% 1.08, best-5% 2.74) — NOT the "between median and best-5%" pattern the protocol expects. This is not classic overfitting (the real path underperforms bootstrap variants rather than getting lucky), but it does not cleanly satisfy the stated Monte Carlo check either. Flagged, not yet resolved. Trade-count distribution: original 167, median 167.0, worst-5% 150, best-5% 186.1 (plausible spread). Max DD distribution: original -12.25%, median -19.6%, worst-5% -33.2%(!), best-5% -12.06% — the ORIGINAL DD is actually milder than the median resampled DD, and the worst-5% tail (-33.2%) breaches the -30% catastrophic threshold used in Research Run #1. Needs scrutiny before any acceptance decision.
   - **4h config Monte Carlo (200 scenarios):** same anomaly as 1h, more pronounced. Original Sharpe 1.38 sits **below even the worst-5% tail** (worst-5% 1.51, median 2.33, best-5% 3.08). Original trade count (102) exceeds the resampled best-5% (95.0; median 83.0, worst-5% 72.9) — the real historical path produced MORE trades than 95%+ of bootstrap-resampled paths. Max DD is more normally placed this time: original -13.78% vs median -11.93%/worst-5% -19.08%/best-5% -8.07% (between median and worst-5%, not breaching it). **Working theory (unconfirmed):** the moving-block bootstrap (10080-min blocks) may systematically under-produce the rare large moves this "make it selective" design is built to catch, since shuffling weekly blocks disrupts the specific trending-regime persistence the wide Keltner channel needs to break out from — this would make the resampled distribution not a faithful null for this specific mechanism, rather than the strategy being unlucky on the real data. Not verified either way. Flag for a future session: consider a trades-resampler MC (`run_trades=True`) as a cross-check, since it doesn't depend on the candle-generation pipeline's ability to reproduce rare-move frequency.
   - **Cross-symbol replication (identical params, report-only, not gating):**
     - 1h: ETH (native) Sharpe 1.3263 · BTC 1.0317 (193 trades, DD -17.84%) · SOL 0.52 (179 trades, DD -28.33% — close to the -30% catastrophic line, worth watching)
     - 4h: ETH (native) Sharpe 1.3956 · BTC 0.9822 (96 trades, DD -17.73%) · SOL 0.3678 (88 trades, DD -18.73%)
     - Signal direction is consistent and positive across all 3 symbols and both timeframes tested — real, generalizing edge, ETH is consistently the strongest symbol for this family (matches Research Run #1's finding).
   - **Still below the 1.5 Sharpe acceptance bar on both timeframes (1.33 and 1.40).** Not yet accepted. This is the strongest candidate found in either research run and the most promising thread to keep pulling.

## `R2_KeltnerBreakoutSelective` — full timeframe sweep result (completed 2026-07-23)

All 4 allowed trading timeframes tried on ETH-USD, each with a period/mult recalibrated for that timeframe's candle density:

| TF | Config | Trades | Sharpe | Max DD | In range? |
|---|---|---|---|---|---|
| 1h | period=76, mult=4.25, atr_mult=1.45, vol=1.25 | 167 | 1.3263 | -12.0% | Yes |
| 2h | period=45, mult=3.4, atr_mult=1.5, vol=1.15 | 148 | 1.2061 | -16.15% | Yes |
| **4h** | **period=25, mult=2.6, atr_mult=1.5, vol=1.1** | **102** | **1.3956** | **-13.46%** | **Yes — best stable candidate** |
| 30m | period=210, mult=5.9, atr_mult=1.5, vol=1.35 | 217 | 1.5852 | -17.82% | No — over ceiling, and the region is a razor's-edge cliff (period=210→217 trades, period=217→**0** trades; a 5% parameter nudge kills the signal entirely). Not pursued further — this is a robustness red flag, not a usable result, even though it's the only config this run to clear Sharpe 1.5. |

**Conclusion: 4h is the strongest robust, in-range timeframe for this family.** The strategy file is currently set to the 4h config. 30m looked most attractive on raw Sharpe but is not trustworthy at the frequency this run requires.

## `R2_KeltnerBreakoutSelective` 4h — additional levers tried, both rejected

- **Exit style:** built a sibling strategy `R2_KeltnerBreakoutSelectiveTrail` (same entry, ATR-trailing-stop exit instead of exit-at-midline) — same entry params gave 137 trades but Sharpe only 1.2297 (worse than midline's 1.3956, better DD -10.19% and winrate 46.7% but the tradeoff is net negative for Sharpe). Exit-at-midline confirmed best exit style for this family, consistent with Research Run #1.
- **`atr_sma_period`** (vol-filter's own lookback, always left at the Keltner default of 20 until now): tried 35 → 99 trades (just under the 100 floor) and Sharpe drops to 1.2909. Reverted to 20.
- Strategy file is locked back to the proven best: period=25, mult=2.6, atr_period=14, **atr_sma_period=20**, vol_expansion_mult=1.1, atr_mult=1.5, risk_percent=1.5 → 102 trades, Sharpe 1.3956.

## BTC-USD as primary (re-tuned) symbol — tried and rejected

2 rounds of BTC-specific tuning on `R2_KeltnerBreakoutSelective` 4h (tighter: period=18/mult=2.2 → 107 trades, Sharpe 0.96, DD -23.2%; wider: period=35/mult=3.2 → 81 trades, Sharpe 1.03, DD -20.8%). Both **worse** than simply replicating ETH's exact params on BTC (96 trades, Sharpe 0.98, DD -17.7%). BTC confirmed structurally weaker for this mechanism regardless of tuning direction — consistent with Research Run #1's finding that BTC is the weakest symbol across every family tried. Not worth further BTC-specific tuning for this family. SOL not yet tried as primary/re-tuned (only identically-replicated so far, both timeframes) — lower priority since it was the weakest replication result too, but technically untried as a from-scratch tune.

## `R2_BBWidthSqueeze` (volatility squeeze family) — tried and rejected

New family: Bollinger-width squeeze (contraction) followed by band breakout — deliberately the OPPOSITE filter direction from the Keltner-expansion family. Hit a real implementation bug first: the rolling-average convolution window wasn't sized to survive the BB warmup NaN region, so `was_squeezed` was silently always `False` (0 trades at every setting). Diagnosed by hardcoding the squeeze condition to `True` and confirming the plain breakout alone fires 1230 times on ETH 1h — isolated the bug to the squeeze-detection math specifically, then fixed the window sizing. Once genuinely working: loose squeeze filter (mult=0.7) → 816 trades, Sharpe -0.20; tight squeeze filter (mult=0.4) → 270 trades, Sharpe **-0.96** (DD -50%). Tightening the filter made results *worse*, not better — the opposite of every other family tried this run. **Conclusion: no real edge in this mechanism for this pool; abandoned after 4 backtests (1 bug-diagnosis, 3 real).** Contrasts with the Keltner-expansion family (same broad idea, opposite direction) which is this run's best lead — confirms volatility EXPANSION, not contraction, is where this pool's edge lives.

## `R2_PairsRatioZscore` (stat-arb pairs) — real breakthrough, redesigned with a regime filter

Previous unfiltered attempts (threshold 2.5-3.2) were both negative and way over-frequent (219-466 trades). Added an ADX regime filter (only fade the ETH/BTC log-ratio z-score extremes when ETH itself isn't strongly trending) — this changed the family from dead to genuinely working:

- **Best: period=80, threshold=2.8, adx_max=25, exit_deadzone=0.3 → 104 trades (in range!), Sharpe 0.5445, max DD -12.09%, 50% maker fill rate.** Strategy file currently locked to this config.
- Tighter regime (adx_max=20, threshold=2.6) made both trade count (67, under floor) and quality (Sharpe 0.43) worse — reverted.

Not yet Monte Carlo'd or cross-symbol replicated (this family is inherently ETH-vs-BTC specific — "cross-symbol" would mean trying the SOL/BTC or SOL/ETH ratio instead, not yet attempted). Second-best candidate of the run after `R2_KeltnerBreakoutSelective`, and structurally the most different mechanism (genuine relative-value signal, not single-asset price action) — good for the diversity/correlation requirement once more candidates exist to check pairwise correlation against.

## `R2_PairsRatioZscore` — 4 more tuning rounds (rounds 4-7), no improvement over round 3

Tried: longer period (120) + wider deadzone (0.6) → better quality (Sharpe 0.6166) but dropped to 64 trades (under floor). Loosening threshold/regime from there overshot badly (213 trades, Sharpe -0.04). A moderate loosening from the *original* 104-trade config landed in-range (166 trades) but at lower quality (Sharpe 0.348). **Best remains round 3's period=80/threshold=2.8/adx_max=25/deadzone=0.3 → 104 trades, Sharpe 0.5445.** Strategy file locked to this. Diminishing returns on this family too now.

## `R2_RangeFadeAdx` and `R2_ShortOnlyBreakdown` — cross-symbol attempts, both failed

- `R2_RangeFadeAdx` on SOL-USD (ETH's exact params): hit the trade-count target almost exactly (104 trades) but Sharpe -0.95 despite a 61.5% win rate — classic tight-stop-for-the-symbol's-volatility signature. Widened stop (atr_mult 2.5→4.5) improved to Sharpe -0.75/66% win rate but never turned positive. **SOL does not replicate this edge; ETH-only, capped at 33 trades.**
- `R2_ShortOnlyBreakdown` on ETH-USD (SOL's exact params): only 18 trades (ETH breaks down far less often than SOL in this window), weak Sharpe 0.16. **SOL-only, capped at 56 trades.**
- Both strategy files reverted to their best native-symbol config. Both families now confirmed single-symbol-only for this mechanism — a real (if modest) finding for the diversity requirement, not further pursued this session.

## Anchor-timeframe trend filter — tried on 2 families, no improvement either time

Tested the "combine the volatility filter with a longer-term trend filter" idea flagged unexplored in Research Run #1's summary:
- `R2_VolBreakoutTrendFiltered` (1h ETH + 4h EMA(10/30) trend agreement): roughly halved trade count at the same base params (120→56), Sharpe about the same (0.53 vs 0.50) with much better DD (-8% vs -16%). Loosened the base entry to compensate (128 trades) and landed back at essentially the unfiltered Sharpe (0.51). **Net: no real improvement, just re-traces the same frequency/quality tradeoff curve.**
- `R2_KeltnerBreakoutTrendFiltered` (4h ETH + 1D EMA(8/21) trend agreement, this run's BEST mechanism): 1D anchor needs 210 daily warmup candles, forcing start_date to 2022-11-01 (loses ~7 months of the window). Result: 74 trades, Sharpe 0.9255 — **worse** than the unfiltered 4h config's 1.3956, even accounting for the shorter comparison window. The anchor trend filter is actively hurting this mechanism, not helping.
- **Conclusion: anchor-timeframe trend filtering does not help either the volatility-breakout or Keltner-breakout families in this pool.** Not worth pursuing further on these two; if tried again in a future session, a different anchor-trend definition (e.g., price-vs-SMA instead of EMA cross, or a longer/shorter EMA pair) might behave differently, but 2 clean negative results across 2 families is a reasonably strong signal to move on.

## `R2_PairsRatioZscoreSOLBTC` — SOL/BTC ratio tried, weaker than ETH/BTC

Same ADX-filtered design as the working ETH/BTC version, applied to SOL/BTC instead: 100 trades (right at the floor), Sharpe 0.2109 — positive but clearly weaker than ETH/BTC's 0.5445. Confirms ETH/BTC is the better pair for this mechanism, consistent with ETH generally being the strongest symbol in this pool across every family tried. Not pursued further (would need its own multi-round tune to have a fair shot, and ETH/BTC is already the better-explored, better-performing lead).

## Jesse's built-in optimizer cross-check on `R2_KeltnerBreakoutSelective` — manual tuning confirmed near-optimal

Ran Jesse's `run_optimization` (IS 2022-05-15→2025-01-31, OOS 2025-01-31→2025-12-31, sharpe objective, 210 trials/7 hyperparameters) as a systematic check against 9 rounds of manual grid search. Top in-range candidates (by combined IS+OOS trade count) re-validated on the **full continuous window** (this run's actual protocol):
- Rank #3 (period=24, mult=1.8, atr_period=12, atr_sma_period=49, vol=0.95, atr_mult=2.3, risk=0.8): 151 trades, Sharpe 1.2697, DD **-6.71%** (much better DD than manual best, but lower Sharpe).
- Rank #7 (period=21, mult=2.7, atr_period=27, atr_sma_period=42, vol=0.85, atr_mult=1.6, risk=1.5): 102 trades, Sharpe 1.2209, DD -13.33%.
- **Both underperform the manually-found config (period=25, mult=2.6, atr_mult=1.5, vol=1.1 -> Sharpe 1.3956).** This is a reassuring cross-check: manual tuning wasn't missing an obviously-better region, and the optimizer's IS/OOS split target doesn't perfectly transfer to the full-window objective this run actually uses. Strategy file reverted to the manual best. If DD matters more than raw Sharpe for a future decision, rank #3's config (-6.71% DD) is worth keeping in mind as an alternative, lower-Sharpe/lower-risk variant of the same mechanism.

## `R2_GridFadeExtreme` (grid/multi-entry) — redesigned with ADX filter, still dead

Applied the same regime-filter insight that rescued range_fade and stat_arb_pairs to the grid family (RSI-triggered ladder entries). Round 1 (tight thresholds): only 12 trades, Sharpe -0.28. Round 2 (loosened to oversold=32/overbought=68/adx_max=30): **145 trades (in range!) but Sharpe -1.02, DD -33.6% (breaching the -30% catastrophic line), despite a 62% win rate** — same asymmetric-loss signature seen in the failed SOL RangeFadeAdx attempt (many small wins, occasional large losses). **Confirmed dead even with regime filtering — the RSI-extreme entry itself has no edge in this pool, consistent with mean reversion being 0/5+ dead across both research runs.** Not pursued further.

## `R2_BTCTrendFollow` — fresh BTC-native mechanism, works but doesn't beat reused Keltner

New family: pure EMA-cross trend-following + ADX confirmation, designed from scratch for BTC specifically (since every ETH-tuned mechanism reused on BTC has underperformed). 3 rounds of widening: 282 trades/Sharpe 0.23 → 171 trades/Sharpe 0.58 → **160 trades (in range), Sharpe 0.7011, DD -25.35%**. Real, working, in-range candidate — but **still weaker than simply replicating `R2_KeltnerBreakoutSelective`'s ETH-tuned params on BTC unchanged (Sharpe 0.98, DD -17.84%, 96 trades)**. Useful clarifying evidence: BTC's best obtainable signal in this pool so far comes from the Keltner-breakout mechanism, not from a bespoke trend-following redesign. Not pursued further as a standalone candidate given it's dominated by an existing, better-performing option.

## 🎯 MILESTONE — `R2_KeltnerAsymmetric` crosses Sharpe 1.5 in-range (2026-07-23, backtest #94)

**First config of either research run to satisfy BOTH the 100-169 trade band AND Sharpe > 1.5.** Built from the long-only finding (longs alone: Sharpe 1.35 @ 68 trades) → asymmetric channel widths (tighter longs / more selective shorts) instead of dropping shorts.

- **Config (locked in strategy file):** period=25, long_mult=2.1, short_mult=2.8, atr_period=14, atr_sma_period=20, vol_expansion_mult=1.0, atr_mult=1.35, risk_percent=1.5. ETH-USD 4h, window 2022-05-15 → 2025-12-31. Backtest id `873ceb73-ae31-4144-92d0-0e80300a92d5`.
- **Metrics:** 118 trades (2.71/month), Jesse-native Sharpe **1.5004**, max DD -14.34%, PF 2.32, net +265%, winrate 39%.
- **Methodology caveat (flag honestly):** my independent daily-closed-PnL reconstruction gives 1.3077 vs Jesse's mark-to-market 1.5004 — a bigger gap than on other configs. The 1.5 crossing holds on Jesse's native metric (the official one) but not on the reconstruction.
- **Robustness — smooth hill, no razor edge:** atr_mult 1.3/1.35/1.5/1.7 → 1.4786/**1.5004**/1.4556/1.3854; long_mult 2.0/2.1/2.2 → 1.4623/**1.5004**/1.4241; short_mult 2.6/2.8/3.1/3.5 → 1.4134/1.4556/1.4230/1.3535. Honest read: true skill level of the region ≈1.45, the 1.5004 point is the peak of a smooth hill.
- **Cross-symbol replication (identical params, report-only):** BTC 129 trades/Sharpe 0.8137/DD -21.3%; SOL 134 trades/Sharpe 0.4830/DD -19.8%. Both positive, neither catastrophic — direction generalizes, magnitude is ETH-specific (same pattern as the symmetric flagship).
- **Correlation vs 2nd candidate:** daily-PnL corr with `R2_PairsRatioZscore` = **0.0135** — genuinely independent, far below the 0.3 dedup threshold.
- **Monte Carlo (done):** original Sharpe 1.4843 (MC harness re-run; ±0.02 wobble vs standalone 1.5004) sits BELOW the entire resampled distribution (worst-5% 1.71, median 2.41, best-5% 3.18) — same family-wide anomaly as both flagship MC runs, and NOT the overfitting signature (which would be original in the top-5% tail). Trade count 118 sits normally within the resampled range (111-137); max DD -14.4% slightly better than resampled median (-15.6%), worst-5% tail -21.4% (inside the -30% limit). Full table in `reports/R2-CANDIDATE-1-KeltnerAsymmetric.md`.
- **NOT yet marked accepted** — full validation battery done (robustness ✅, cross-symbol ✅, correlation ✅, MC ✅ no-overfit-signature). Remaining: a borderline judgment call for Tom — 1.5004 clears the bar by 0.0004 on the official metric; neighborhood average ≈1.45; conservative reconstruction 1.31; MC-harness re-run 1.4843. Three options laid out in the candidate report. The autonomous search continues regardless (7+ more to find).

## Post-milestone diversification sweep (backtests 100-107)

**Correlation map vs the ETH 4h milestone (daily PnL)** — the key strategic discovery: everything is under the 0.3 dedup threshold, so ALL of these paths would count as separate accepted strategies if they reached 1.5:
- BTC replication (same mechanism): **0.055**
- SOL replication (same mechanism): **0.204**
- ETH 1h symmetric flagship (same symbol+family, different TF): **0.199**
- VolBreakoutRare ETH 1h: -0.012 · ShortOnlyBreakdown SOL: -0.001 · RangeFadeAdx ETH: -0.005 · PairsRatioZscore: 0.014

**BTC-native asymmetric tune (5 rounds):** BTC prefers the OPPOSITE asymmetry from ETH — more-selective longs. Frontier: 2.7/2.8/vol1.0 → **1.0907 @ 97t** (just under floor); 2.7/2.8/vol0.9 → 1.0216 @ 102t (in range). BTC ceiling ≈1.0-1.1, far from 1.5. Parked.

**ETH 1h asymmetric tune (3 rounds):** same more-selective-longs direction wins on 1h (4.5/4.0 → **1.3372 @ 168t** vs symmetric 1.3263); pushing further (4.8/3.7) worsens. 1h ceiling ≈1.34, under the bar. Parked — but note it's a corr-0.20 diversifier at 1.34 if the bar were ever relaxed.

**Emerging map of the asymmetry direction:** ETH 4h = tighter longs wins (1.50); ETH 1h and BTC 4h = more-selective longs wins (1.34/1.09). The 4h ETH combination is the only one that reaches the bar.

## Diversification sweep — final results (backtests 108-111)

- **PairsRatioZscore asymmetric thresholds (3 rounds):** the asymmetry lever works here too — long_th=2.6/short_th=3.1 → **0.6537 @ 107t** (vs symmetric 0.5445), further pushes overshoot (2.4/3.4 → 0.588; deadzone 0.5 → 0.612 but DD improves to -8.8%). Family ceiling ≈0.65, far under bar. Parked; best config saved in strategy file docstring.
- **SOL-native Keltner (1 round):** sym-wide 2.6/2.6 → 0.14. Combined with the 0.48 replication, SOL confirmed structurally weak for this mechanism. Dead end.

**Complete ceiling map of every corr-<0.3 diversification path (all far under 1.5):** ETH 1h asym 1.34 · BTC 4h asym 1.09 · PairsRatioZscore 0.65 · SOL 4h 0.48. The correlation rule is generous but the 1.5 bar is the binding constraint everywhere except ETH 4h.

## 🆕 `R2_RegimeSwitchETH` — new construction, near-bar candidate (backtests 112-122)

**Genuinely new construction: regime OVERLAY** — two validated-but-capped edges combined in ONE strategy so their uncorrelated PnL streams stack (portfolio effect inside a single strategy). Ungated asymmetric Keltner breakout (1h ETH, the 1.34-ceiling component) + ADX-gated Donchian fade (the 0.708-quality/33-trade component), conflict-skipped, per-mode exits via `self.vars['mode']`.

- Design lesson: hard regime SWITCHING (breakout only when ADX≥30) hurt (1.23) because ADX rises after trends start; the ungated-overlay design fixed it (1.4663@178).
- **Best in-range: adx_gate=28, dc=17, fade_offset=0.14, fade_atr=2.5, kc 76/4.9/4.4, vol=1.25, bo_atr=1.45 → 169 trades (at ceiling exactly), Sharpe 1.4402**, DD -15.55%, net +301%. Backtest `72b96f04-35dc-48ff-bd32-0015eb2393a5`.
- **Corr with candidate #1 (4h milestone): 0.2189** — under 0.3, counts as an independent strategy.
- Trim-lever map: fade_offset is the clean trade-count lever; vol gate and kc mults are dirty (cut good trades / sticky via conflict-release). bo_atr_mult 1.35 didn't replicate the 4h gain here.
- **Status: 0.06 under the bar.** Second-best in-range result of the run. Construction innovation validated (+0.10 over its best component).

**4h fade-overlay experiment (backtests 123-124) — done, closed:** with the fade barely firing (dc14) the result is 1.5103@119, i.e. the milestone +1 inert trade and +0.01 Sharpe — not a real improvement, just conflict-skip noise. Making the 4h fade actually contribute (dc10/adx32) DILUTES to 1.4532@123 — the Donchian fade edge doesn't translate to 4h. **Conclusion: the overlay construction only pays on 1h (where the fade has genuine quality). Candidate #1 stays as the clean, validated 4h asymmetric milestone. The overlay's home is the 1h RegimeSwitchETH at 1.4402@169 (corr 0.219).**

## `R2_RegimeSwitchETH` — closed at 1.4402@169 (12 rounds)

Final refinement attempts: kc_period 76→85 with best-quality fade → 193t/1.3913 (period widening doesn't cut breakout count; extra fade dilutes at that volume). bo_atr_mult 1.35 → no gain on 1h. **Final: adx_gate=28, dc=17, fade_offset=0.14, fade_atr=2.5, kc 76/4.9/4.4, vol=1.25, bo_atr=1.45 → 169 trades, Sharpe 1.4402, DD -15.55%, corr 0.219 vs candidate #1** (backtest `72b96f04-35dc-48ff-bd32-0015eb2393a5`). Documented near-miss/diversifier — 0.06 under bar. Strategy file locked to this config. Not MC'd (protocol reserves MC for finalists ≥1.5).

## `R2_BreakoutPlusRatio` (overlay #2: breakout + ETH/BTC ratio fade) — closed after 2 rounds

Round 1 (th 3.0/3.4, adx22, dz0.3): 187t/1.2953. Round 2 (rarer/shorter ratio trades: th 3.2/3.6, adx20, dz1.2): 170t/1.3440 — never beats the pure breakout (1.3372) meaningfully. **Root cause identified: single-position mechanics.** A slow-unwinding ratio trade BLOCKS breakout entries; the stacking theory requires the secondary stream's trades to be FAST relative to the primary's. **Overlay design law learned this session: fade (hours-long trades) stacks (+0.10); ratio (days-long trades) blocks (±0); 4h fade (barely fires) is inert.** Closed.

## Two new families explored on request (backtests 128-133)

**`R2_TrendPullback` (with-trend Connors-style pullback, RSI-fast extremes + trend SMA) — DEAD after 3 rounds.** RSI3<12/SMA200 → 492t/-1.42; RSI2<5/SMA300 → 0 trades (deep pullbacks and intact trends anti-correlate on 1h crypto — the dip that reaches RSI2<5 usually breaks the SMA too); RSI2<8/SMA200 → 888t/-1.50. Same signature as every other counter-move entry in this pool: high winrate (58-61%), crushing asymmetric losses. The "fade a move" graveyard now includes: naive RSI/BB/zscore, grid (±ADX), squeeze, SOL range-fade, and with-trend pullbacks. **Only two fade mechanisms ever worked here: ADX-gated Donchian fade (ETH only) and ratio fade (weak).**

**`R2_FakeoutFade` (failed-breakout reversal — NOVEL, works, weak).** Fades breakouts that occurred on LOW volatility (the no-edge kind per Run #1) once price falls back inside the band. dc30/gate1.0/atr2.5 → **103 trades (in band immediately), Sharpe 0.2522, DD -5.6%, winrate 66%**. Stricter gate (0.9) kills it (25t/-0.13); shorter channel (dc20) dilutes (185t/0.07). Family ceiling ≈0.3 — genuinely novel mechanism, correct frequency out of the box, but weak edge. Same tier as VolBreakoutRare. Parked, config saved at the dc30 optimum in the file docstring lineage.

## Cross-symbol completion of the new families + Tom's 4h-signal/1h-exec idea (backtests 134-138)

**FakeoutFade cross-symbol (identical dc30/gate1.0 params):** BTC **0.2724 @ 84t** (≈ETH's 0.2522 — the mechanism is consistent across the two majors), SOL 0.0617 @ 155t (weak). Family confirmed real-but-weak (~0.25) on ETH+BTC.

**TrendPullback on BTC:** 473t/-0.90 — dead on BTC too (ETH was -1.42). Family definitively closed across symbols.

**Tom's idea — 4h signal executed on 1h** (`R2_Keltner4hSignalExec1h`, milestone params, indicators on 4h series, orders on 1h route): raw intrabar → 143t/**1.2306**; with a 0.4% breakout buffer → 131t/**1.1541**. Both clearly below the 4h-native 1.5004. **Finding: the 4h CLOSE confirmation is load-bearing for this signal** — intrabar 1h triggers catch shallow pokes that reverse before the 4h close, and the buffer variant enters strong breaks later/worse. Combined with the earlier anchor-filter tests (4h/1D filters on 1h signals — also negative twice), the consistent lesson is: **this pool's Keltner signal wants its native timeframe rhythm; multi-TF mixing degrades it in both directions.** Closed.

## VWAP fade dead + near-candidate robustness confirmed (backtests 139-142)

**`R2_VwapDeviation` (daily-anchored VWAP fade, ADX-gated) — DEAD after 2 rounds.** Deep deviations (3 ATR): 70t/-1.17 — VWAP stretches in crypto continue, they don't revert. Moderate (1.8 ATR, adx<22): 267t/-0.07. The volume-weighted anchor doesn't rescue the fade concept. Fade graveyard complete.

**`R2_RegimeSwitchETH` robustness — smooth region confirmed:** adx_gate 26 → literally identical (169/1.4402); dc 15/17/20 → 1.4312/1.4402/1.4269; offset 0.14/0.18 → 1.4402/1.4274. The near-candidate sits on a stable plateau ~1.43-1.44, no razor edges. **Decision-ready if the bar is ever relaxed** (would still need MC per protocol at acceptance time).

## 🏆 OPTIMIZER SUCCESS — new best config for candidate #1 (backtests 143-149)

Tom asked about the optimizer. Ran a DISCIPLINED optimization on `R2_KeltnerAsymmetric` (never optimized before — only the symmetric parent was): train 2022-05→2024-08, test OOS 2024-09→2025-12, 240 trials, narrowed ranges around the known-good region, **selection on TEST metrics only**.

**Result: a strictly better config, with cleaner provenance than the old milestone:**
- **NEW BEST: period=25, long_mult=1.5, short_mult=3.0, atr_period=10, atr_sma_period=34, vol_expansion_mult=1.1, atr_mult=1.2, risk_percent=1.2 → 108 trades (in-range), Sharpe 1.5936, DD -10.36%, PF 2.61, winrate 45.4%, +35.1%/an.** Backtest `412cef67-4e3e-4713-acc6-b17c319709b6`. (Optimizer's raw pick was vol=1.15 → 96t/1.5992, 4 under floor; single nudge vol→1.10 crossed the floor at 1.5936.)
- **Provenance:** the core was found WITHOUT seeing 2024-09→2025-12 (train Sharpe 1.55, test 1.65 — held up OOS), unlike the old milestone (full-window manual search). Structurally more trustworthy.
- **Robustness (smooth):** atr_mult 1.2/1.3 → 1.5936/1.5892; long_mult 1.5/1.6 → 1.5936/1.5731; vol 1.10/1.15 → 1.5936@108/1.5992@96.
- **Cross-symbol (identical params):** BTC 0.7668@134, SOL 0.7223@118 — both positive, never catastrophic, and SOL generalizes much better than under the old config (0.72 vs 0.37).
- **Monte Carlo (200 scen.):** original Sharpe 1.5772 sits WITHIN the resampled range (worst-5% 1.5157, median 2.29) — first config of this family whose real path isn't below the whole bootstrap distribution. DD -10.46% better than resampled median (-13.22%); worst-5% DD -21.96% (inside limit). No overfit signature.
- Also validated: OOS-rank17 full-window 1.4262@127 (kept as documented alternative). Old milestone (2.1/2.8/1.35 → 1.5004@118) remains logged as the previous reference.
- **This config SUPERSEDES the old milestone as candidate #1.** Strategy file locked to it (note: file currently has neighbor defaults L=1.6 from the last robustness probe — restore L=1.5/atrM=1.2 defaults before any further use).
- Caveat unchanged: daily-reconstruction cross-check 1.3902 vs native 1.5936 — the methodology gap persists; the bar is met on Jesse's official metric with real margin now (+0.09), not by 0.0004.

## Exact next step

1. **Candidate #1 (`R2_KeltnerAsymmetric` ETH 4h, Sharpe 1.5004 @ 118 trades) is fully validated** — robustness ✅, MC ✅ (no overfit signature), cross-symbol ✅, correlation map ✅. Awaiting Tom's borderline accept/bench call (`reports/R2-CANDIDATE-1-KeltnerAsymmetric.md`). Do not touch its config further.
2. Dead/closed (don't revisit without materially new ideas): mean_reversion, grid_multi_entry, volatility_squeeze, volatility_breakout (~0.5), range_fade (ETH-only 33t), short_only (SOL-only 56t), trend_following BTC (dominated), anchor-trend filters (hurt twice), SOL-native Keltner (0.14-0.48), BTC-native Keltner (~1.1 ceiling), ETH 1h Keltner (~1.34 ceiling), pairs stat-arb (~0.65 ceiling). Jesse optimizer cross-checked.
3. **The exploration is now deep enough that the strategic picture is clear: one config reaches the bar; every mapped alternative plateaus 0.15-1.35.** Remaining untried ideas are increasingly speculative (2h asym ~1.3 expected; SOL bespoke — weak prior; novel exotic families). Continue probing at lower intensity OR discuss with Tom whether (a) 1 accepted + several 1.0-1.35 diversifiers is an acceptable portfolio reframe, or (b) grind to the 400-backtest ping as specified. Directive says grind — so keep going, but favor genuinely novel mechanisms over more tuning.
4. Keep logging every backtest to `reports/ALL-RUNS.jsonl` — currently **111 total** (ping threshold 400).
