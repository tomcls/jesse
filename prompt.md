can you access the mcp server in order to create strategy, run backtest,...?
I need you to act as 24/7 Quant agent who can perform research. At the end, I am going to need 10 different trading strategies.
Each of them must have a Sharpe ration above 1.5 over the past four years.
It doesn't matter if you try hundreds of different strategies or versions of them
When you run montecarlo simulation, i want the Sharpe ration of the original backetest to be positionned in the middle between the median and the best 5%.
In fact, the nearer  it is to the median, the better, as it would be less likely to be overfit.



you do not have to only one symbol for this; it ok to try different trading symbols:
BTC-USD, BNB-USD, ETH-USD, XRP-USD, SOL-USD
It's okay for you to find multiple strategies on the same. So do not feel pressured to absolutly use all the symbols.
Make sure to find me all sorts of tradng strategies and not just trend following. So mean reversion or maybe even grid strategies where we enter and exit at multiple points, those are all fine.
Notice that some of these symbols are lowercap altcoins. Some of them are so volatile or pool quality that their prices are more likely to go down; this could be an oppertunity to develop a short-only strategies. You do not have to use
the same parameters for long and short trades, but i will leave that decision to your researcher agent.
You can also come up with whichever timeframe that works the best. However, I would prefer it was either 30 minutes and one hour.

Feel free to also use an anchor timeframe, such as 4 hours, in your analysis, but not for trading timeframe.
The most important part is not to stop until you have found all 10 strategies.
In the meatime, feel free to keep updating different report files in markdown format so that I can easily monitor your progress. Keep the reports in a new folder called "reports" inside your project dir.

This may take hours or even days, and that is perfectly fine with me. you should be thinkings about of hundreds of backtests before stopping.
Do not interrupt to ask for permission; I trust your judgment. Only ping me if
something is wrong and you absolutly need my input.

I do not want that you use sub agents for running things

################################

# Autonomous Quant Research Agent — Jesse MCP

You have access to the Jesse MCP server (localhost:9002) to create strategies, import candles, run backtests, rule significance tests, Monte Carlo simulations and optimizations. Act as an autonomous quant researcher. Read STATE.md at the start of every session before doing anything else; if it exists, resume from where it says.

## GOAL

Deliver 10 trading strategies that each pass the FULL validation protocol below. Quality over speed: this may take days and hundreds of backtests, which is fine.

## DATA & EXECUTION CONTEXT

- Exchange: **Kraken Pro Futures**. This is where the strategies will run live. Never import, research, or validate on data from any other exchange.
- Available history: from ~2022-04-01 → today (~4.3 years). Before anything else, verify the actual first available candle date per symbol and log it in STATE.md. Pay special attention to data quality around May 2022 (Luna collapse) and November 2022 (FTX) — thin books during panic days can produce degenerate candles; report anything suspicious.
- Symbols: BTC-USD, ETH-USD, SOL-USD, XRP-USD. First verify each pair exists on Kraken Futures with sufficient history; drop any that doesn't and log why. Multiple strategies on the same symbol are fine; using every symbol is not required.
- Trading timeframes: **30m or 1h only**. Anchor timeframes (e.g. 4h) are allowed for analysis/filters, never as the trading timeframe.
- Backtest settings: futures mode, realistic Kraken Futures fees (**0.02% maker / 0.05% taker**), pessimistic slippage on market orders. Prefer strategies that enter with limit orders; model the fee difference correctly.

## RESEARCH FUNNEL — apply the full protocol only to survivors

Work as a funnel. Never run the full validation on an idea that hasn't earned it:

- **Stage 0 — Rule significance test.** Before building any full strategy around an entry signal, run Jesse's rule significance test (signal vs. thousands of random-entry simulations). If the signal is indistinguishable from random entries, the idea is dead: one line in REJECTED.md, move on. This is the cheapest kill and should eliminate most ideas.
- **Stage 1 — Quick IS screen.** Single backtest on one in-sample window only. Kill anything with clearly poor Sharpe, too few trades, or absurd drawdown. One line in REJECTED.md.
- **Stage 2 — Full walk-forward.** Only for candidates that pass stages 0-1: the complete 4-fold protocol below.
- **Stage 3 — Finalists.** Monte Carlo, decorrelation, holdout, final calibration — only for candidates that pass all 4 folds.

**Batch your work**: launch several backtests per reasoning cycle (e.g. a grid of variants at once), then analyze results as a group. Avoid one-backtest-per-thought loops — same compute, far less orchestration overhead.

## VALIDATION PROTOCOL (non-negotiable)

### Walk-forward, 4 folds
- Fold 1 — IS: 2022-04 → 2023-10 | OOS: 2023-11 → 2024-04
- Fold 2 — IS: 2022-10 → 2024-04 | OOS: 2024-05 → 2024-10
- Fold 3 — IS: 2023-04 → 2024-10 | OOS: 2024-11 → 2025-04
- Fold 4 — IS: 2023-10 → 2025-04 | OOS: 2025-05 → 2025-10
- The remaining months (2025-11 → today) stay untouched as a final holdout: run each accepted strategy on it once, at the very end, as an extra sanity check.
- Adjust fold boundaries proportionally if the real first-candle date differs, keeping the structure: rolling IS ≈ 18 months, OOS ≈ 6 months, 4 folds covering distinct market regimes (fold 1 deliberately includes the 2022 bear market in its IS).
- OOS windows are UNTOUCHABLE during research and tuning of that fold. One single OOS run per candidate per fold. If a candidate fails a fold's OOS, it is dead in that form — never re-tune it on OOS data. Go back to in-sample research with a materially different idea, and log the failure in REJECTED.md.
- When using Jesse's built-in optimization, its train/test split must respect the same discipline: optimize only inside the fold's IS window, never let the optimizer see any OOS or holdout data.

### Acceptance criteria — ALL required
1. **Sharpe > 1.5 on OOS in at least 3 of 4 folds**, and the remaining fold must not be catastrophic (OOS Sharpe > 0 and max drawdown within limits). In-sample metrics are for research only and never count as validation.
2. **≥ 100 closed trades** over the combined full period (fewer trades = statistically meaningless Sharpe → reject).
3. **Monte Carlo** (trade-order shuffle + candle-based simulation) on each passing fold: the original backtest Sharpe should sit near the MEDIAN of the simulated distribution. The closer to the median, the better (less likely overfit). Reject if it sits in the top 5% tail of its own distribution.
4. **Max drawdown < 30%** on every OOS window.
5. **Decorrelation**: pairwise correlation of daily returns with EVERY already-accepted strategy < 0.3, measured on the OOS periods. If two candidates both pass but correlate, keep the more robust one and log the other in REJECTED.md.

### Final calibration (only after a strategy is accepted)
- Re-fit the accepted strategy's parameters on the most recent 18 months only. The walk-forward validated the LOGIC; this step calibrates the PARAMETERS to the current regime.
- Run one final backtest of the re-fitted version on the last 6 months as a sanity check (not a validation — just confirm nothing is broken).
- The re-fitted version is the deliverable that goes to paper trading.

## STRATEGY DIVERSITY

- Not all trend following. Across the 10 accepted strategies, include genuinely different logics: mean reversion, breakout, grid-like multi-entry/multi-exit, volatility-based — different mechanisms, not parameter variants of one idea.
- Long/short parameters may differ. Short-only strategies are allowed only if the data justifies them, not by assumption.

## PROCESS & REPORTING

- Maintain a `reports/` folder in the project dir:
  - One markdown file per ACCEPTED strategy: logic description, parameters, all metrics per fold (IS + OOS), Monte Carlo results, correlation with other accepted strategies, holdout result, re-fitted final parameters.
  - `REJECTED.md`: one line per failed candidate — name, symbol, timeframe, funnel stage reached, which criterion killed it.
  - `STATE.md`: current progress, accepted count, what you are working on, exact next step. Update it every cycle. This file is your memory across sessions — sessions WILL be interrupted (usage limits), so keep it always current enough that a cold restart loses nothing.
- Expect hundreds of backtests. Do not stop until 10 strategies pass — but **NEVER relax, reinterpret, or silently lower any acceptance criterion to get there**. If after extensive search a criterion appears unreachable (e.g. decorrelation makes strategy #9 impossible), STOP and ping me with the evidence and your analysis. Changing the rules is my decision, not yours.
- Sanity duties: if you detect data gaps, degenerate candles, API errors, or results that look too good to be true (Sharpe > 4, win rate > 80%), treat it as a data/logic bug first. Investigate before celebrating.
- No subagents. Do not ask permission for routine work. Only ping me if blocked, if a criterion seems unreachable, or if something looks wrong.

#############################################################################################"

# Pipeline Dry Run — Validate Before the Real Research Run

This is NOT a strategy research task. The goal is to verify, end to end, that every mechanical step of the upcoming quant research pipeline works on this machine. The strategy used here is deliberately dumb and its performance is irrelevant. Do NOT optimize it, do NOT try to make it profitable, do NOT iterate on it.

You have access to the Jesse MCP server.

## TEST STRATEGY (fixed, do not tune)

A basic EMA crossover on BTC-USD, Kraken Pro Futures, 1h timeframe:
- Long when EMA(20) crosses above EMA(50), close the long on the opposite cross.
- Short when EMA(20) crosses below EMA(50), close the short on the opposite cross.
- Fixed position size, no leverage subtleties, market orders.

## CHECKLIST — run in order, log every result

### 1. Data availability
- Import candles for BTC-USD on Kraken Pro Futures, requesting from 2023-01-01.
- Report: exact date of the FIRST available candle, exact date of the last one, total candle count on 1h.
- Scan for gaps or degenerate candles (zero volume across long stretches, identical OHLC repeated, missing periods). Report anything suspicious with dates.
- Repeat the first-candle check (quick, no full gap scan needed) for ETH-USD, SOL-USD, XRP-USD. Report a small table: symbol → first candle date → usable history length.

### 2. Backtest mechanics
- Run the test strategy on ONE full year of data.
- Verify in the results that fees are actually applied at Kraken Futures rates (0.02% maker / 0.05% taker) and that slippage settings are active. Report the fee total vs. gross PnL so I can see fees are non-zero.
- Report: number of closed trades, Sharpe, max drawdown, execution time of the backtest.

### 3. Walk-forward mechanics
- Using the real first-candle date from step 1, compute the 3 fold boundaries (rolling IS ≈ 18 months, OOS ≈ 6 months, as defined in the main research prompt) and print them explicitly.
- Run the test strategy on each fold's IS and OOS windows separately (6 backtests total).
- Report per fold: window dates, trades, Sharpe, drawdown. Again: the numbers being bad is expected and fine — what matters is that all 6 runs complete without errors and the windows fall inside available history.

### 4. Monte Carlo mechanics
- Run Jesse's Monte Carlo (both trade-order shuffle and candle-based simulation) on one of the fold backtests.
- Report: does it complete, how long does it take, where does the original Sharpe sit in the simulated distribution (percentile). Note the runtime — I need to know if this step is a bottleneck for a run involving hundreds of candidates.

### 5. Correlation mechanics
- Run the test strategy on BTC-USD and (with identical parameters) on ETH-USD over the same window.
- Extract both daily-returns series and compute their pairwise correlation. Report the number.
- This validates the decorrelation check used in the main run. If daily returns are not directly exposed by the MCP/API, figure out the cleanest way to compute them and document the method in the report.

### 6. Reporting & state mechanics
- Create the `reports/` folder. Write `DRYRUN.md` containing all results above, structured.
- Create `STATE.md` and `REJECTED.md` with placeholder structure matching the main research prompt, to confirm write access and format.

## RULES

- If ANY step fails, do not work around it silently: report the exact error, your diagnosis, and your proposed fix, then continue with the remaining steps if possible.
- At the end, give me a clear GO / NO-GO verdict: either "all 6 steps pass, the pipeline is ready for the research run" or the list of blockers with severity.
- Total expected duration: this should take well under an hour. If a step takes drastically longer, that itself is a finding — report it.