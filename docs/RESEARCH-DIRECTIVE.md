# Quant Project — Context & Roadmap
> Session memo — 2026-07-21. Purpose: give Claude Code full context of decisions made, and serve as Tom's checklist for the steps AFTER strategy generation. Read this alongside STATE.md at session start.

## 1. Context & decisions already made

### Exchange: Kraken Pro Futures — final decision, evidence-based
- Post-MiCA (July 1, 2026 deadline), crypto perps require a **MiFID II** license, not just MiCA. Almost nobody has both.
- Eliminated: Binance (no MiCA license, Greece rejected, uncertain EEA access), Bybit EU (MiCA yes, but SPOT ONLY — no derivatives license yet), Bitfinex (no license at all, silent), Gate (MiCA yes, derivatives no).
- Only real candidates for a Belgian resident: **Kraken** (MiCA + MiFID derivatives + native Jesse support) and OKX X-Perps (MiFID-regulated, deeper liquidity, but NO Jesse driver → custom development needed).
- Kraken futures fees = 0.02% maker / 0.05% taker (same as Binance; the "Kraken is expensive" objection applies to SPOT only).
- Liquidity concern dismissed at our size: $1,000 positions are negligible vs. book depth. Real caveat: thinner books = more violent wicks during volatility spikes → pessimistic slippage in backtests, prefer limit orders.
- Kraken perps are quoted in **USD (fiat), multi-collateral** (USD, USDC, BTC...) — no USDT dependency, cleaner post-MiCA. The BTC-USD pair in Jesse is correct.

### Data
- Kraken Pro Futures history available from **~2022-04-01** (~4.3 years) → original 4-year validation rule feasible, AND the window includes the 2022 bear (Luna May 2022, FTX Nov 2022) = the previously missing regime.
- Import is slow and must be done **in sequential batches** (parallel imports crash / rate-limit). Interrupted imports resume cleanly (duplicate candles skipped).
- Status at time of writing: BTC done, ETH in progress, SOL & XRP pending.
- If the machine feels slow during imports, check `top` for claude-desktop CPU runaway (known issue) before blaming Kraken's API.

### Research protocol (full version in quant-agent-prompt v2)
- Funnel: Stage 0 significance test → Stage 1 quick IS screen → Stage 2 walk-forward 4 folds → Stage 3 finalists (MC, decorrelation, holdout).
- 4 rolling folds (IS ≈ 18mo / OOS ≈ 6mo) from 2022-04; final holdout = 2025-11 → today, touched once at the very end.
- Acceptance: OOS Sharpe > 1.5 on ≥ 3/4 folds; ≥ 100 closed trades; MC median criterion; max DD < 30% OOS; pairwise correlation < 0.3 vs accepted strategies.
- Final calibration: re-fit params on last 18 months (walk-forward validates the LOGIC, re-fit calibrates the PARAMS to current regime).
- Anti-gaming rules: never relax criteria silently; too-good-to-be-true results (Sharpe > 4, WR > 80%) = investigate as bug first; STATE.md updated every cycle (sessions WILL be cut by usage limits).
- Model: **Sonnet 5** for the grind; periodic audits of reports/ by a stronger model (Opus/Fable), esp. REJECTED.md and real diversity of accepted strategies. Compute (backtests/MC) is local and free; quota is spent on reasoning → batch backtests per reasoning cycle.

## 2. Pipeline order — where we are

1. ✅ Prompts written: pipeline-dry-run-prompt + quant-agent-prompt v2 (with funnel)
2. ⏳ Data import (sequential batches) — IN PROGRESS
3. ⬜ **DRY RUN** (~1h): validates the 6 mechanics end-to-end → GO/NO-GO
   - Outputs to review: first-candle table per symbol (adjust folds if needed), data gaps around May/Nov 2022, fees actually applied, Monte Carlo runtime (→ throughput per 5h quota window), method for extracting daily returns (needed for correlation checks)
4. ⬜ **RESEARCH RUN** (days/weeks, pulsed by quota windows): until 10 strategies pass — or until the agent pings with evidence that a criterion is unreachable (changing rules = Tom's decision only)
   - Audit rhythm: review reports/ every ~24h at first (criterion-gaming, fake diversity); space out if Sonnet 5 holds discipline

## 3. AFTER the strategies are generated — do not forget

### Phase A — Paper trading (6-8 weeks, criteria-based, not calendar-based)
- All 10 strategies in paper on Kraken.
- **SHADOW BACKTEST — the key test** (weekly): run the backtest on exactly the elapsed period, compare with paper trade-by-trade:
  1. Signals: same trade, same candle, same direction. Expected match = 100%, binary. One divergence = mandatory investigation (lookahead, candle timing, streaming-vs-batch indicator computation).
  2. Position sizes: quantify rounding gaps (Kraken min quantities vs fractional backtest positions).
  3. Fill prices: weakly informative in paper (simulated); becomes the gold metric in live.
  - Trap: shadow backtest must run on candles AS THE LIVE SAW THEM (log them at decision time); re-imported candles may differ slightly.
- Paper exit criteria: 0 mechanical errors over last 4 weeks + ~100% signal match + observed slippage/fees within modeled assumptions.
- P&L over 6-8 weeks is pure noise — do NOT judge performance on it. Performance was validated by the 4 folds; paper is an integration test.
- Paper is structurally OPTIMISTIC on limit-order fills (simulated fills ignore queue position) → don't extend paper hoping to learn more; only live measures real fills.

### Phase B — Live deployment ($1,000 per strategy, $10k total max)
- Go live **per strategy** as each has 5-6 clean paper trades — not all 10 at once; no reason to wait for the slowest.
- BEFORE first real euro, settle **strategy isolation**: sub-accounts (one API key per strategy, full isolation, clean accounting) vs single margin account (shared collateral = one strategy's balance affects others' sizing — a coupling the backtests never simulated). Check how Jesse handles multi-strategy live on one exchange.
- First 3-6 months of live = real execution validation: same shadow-backtest discipline with real fills. Deliverable: measured live-vs-backtest gap per strategy.
- Let compounding run (sizing follows current balance, exactly as the backtest did). Withdrawing profits mid-cycle = intervention = methodological gap vs backtest.
- +20% in a month = red flag, not champagne: a Sharpe 1.5 strategy does ~20-40%/YEAR. Immediate shadow backtest; if it doesn't show the same, it's a bug.

### Phase C — Maintenance loop (3 cadences, nothing discretionary in between)
1. **Continuous monitoring** (automatable — future Alfred job, deferred):
   - Auto-suspend if live drawdown exceeds worst backtest fold DD + margin (write the exact number per strategy BEFORE going live).
   - Rolling 90-day Sharpe vs the distribution of 90-day Sharpes from the 4-year backtest (agent can compute it): below 5th percentile = statistical signal → suspend to paper (bench), not straight to trash.
   - Continuous shadow backtest: signal divergence = bug (different treatment than alpha decay).
2. **Semi-annual re-calibration**:
   - Add a new walk-forward fold with the 6 new months of data; re-fit params on rolling last 18 months.
   - Logic NEVER changes during re-calibration (new logic = new strategy = full protocol from scratch).
   - Parameter stability across re-calibrations is itself a health indicator (jumpy params = no structural edge).
   - Also the ONLY moment for capital decisions: scale strategies whose live/backtest gap stayed clean, cap/skim if desired, replace dead strategies from the bench.
3. **Continuous research (the factory)**:
   - Research keeps running at low intensity (e.g. one quota weekend/month) → validated candidates go to the BENCH (paper-traded, ready, not deployed).
   - When a live strategy dies, the best decorrelated bench candidate takes its place and capital. Never search in emergency.

### Golden rules (apply to Tom as much as to the agent)
- No manual intervention between cadences. No "I don't feel it this week" cuts, no "it's crushing it" doubling. Rules decide; Tom decides the rules, at the scheduled moments.
- Ambiguous mid results will tempt criterion-tweaking — "changing the rules is my decision, not yours" applies to Tom's future self too.
- The project's success metric ≠ number of strategies found; it's the reliability of what passes the filter. "Seven, not ten" — or even "they don't beat BTC buy-and-hold after fees" (the silent benchmark) — is the protocol WORKING, not failing.

## 4. Deferred / parked
- **Alfred as quant butler**: consume Jesse MCP (or REST API localhost:9000, or Postgres read-only) for monitoring + weekly shadow backtest + threshold alerts. Channel hierarchy: MCP → REST → DB read-only → logs (last resort, brittle). Deferred until there are live strategies to watch.
- **Monitoring prompt** (3rd of the series): weekly shadow backtest + 3 comparison levels + suspension thresholds. To write when paper starts.
- OKX X-Perps: fallback exchange if Kraken live driver disappoints; would need a custom Jesse driver (agent-writable, added bug surface).
- **Check Jesse live-trading supported exchange list** (separate from the import list) — still unverified for Kraken. **Do this before the paper phase.**