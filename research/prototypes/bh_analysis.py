#!/usr/bin/env python3
"""Buy-and-hold benchmark analysis for BTC/ETH/SOL (daily closes, Kraken Pro Futures proxy).
Window: 2022-04-25 -> 2025-12-31 (research window; holdout excluded)."""
import csv, math
from collections import defaultdict
from datetime import date

PATH = "data-binance-daily-closes.csv"
W0, W1 = date(2022, 4, 25), date(2025, 12, 31)

series = defaultdict(dict)
with open(PATH) as f:
    for sym, d, close in csv.reader(f):
        dd = date.fromisoformat(d)
        if W0 <= dd <= W1:
            series[sym][dd] = float(close)

def stats(closes_by_day):
    days = sorted(closes_by_day)
    px = [closes_by_day[d] for d in days]
    rets = [px[i] / px[i - 1] - 1 for i in range(1, len(px))]
    n = len(rets)
    mean_r = sum(rets) / n
    std_r = math.sqrt(sum((r - mean_r) ** 2 for r in rets) / n)
    sharpe = mean_r / std_r * math.sqrt(365)
    total = px[-1] / px[0] - 1
    years = (days[-1] - days[0]).days / 365.25
    cagr = (px[-1] / px[0]) ** (1 / years) - 1
    # drawdown
    peak, mdd, trough_d, peak_d, cur_peak_d = px[0], 0.0, days[0], days[0], days[0]
    uw_start, max_uw, cur_uw_start = None, 0, days[0]
    longest_uw = (0, None, None)
    for i, p in enumerate(px):
        if p >= peak:
            peak = p
            cur_peak_d = days[i]
            uw = (days[i] - cur_uw_start).days
            if uw > longest_uw[0]:
                longest_uw = (uw, cur_uw_start, days[i])
            cur_uw_start = days[i]
        dd_ = p / peak - 1
        if dd_ < mdd:
            mdd = dd_
            trough_d = days[i]
            peak_d = cur_peak_d
    # still underwater at end?
    uw = (days[-1] - cur_uw_start).days
    if uw > longest_uw[0]:
        longest_uw = (uw, cur_uw_start, None)
    calmar = cagr / abs(mdd) if mdd else float("inf")
    return dict(start=px[0], end=px[-1], total=total, cagr=cagr, sharpe=sharpe,
                mdd=mdd, peak_d=peak_d, trough_d=trough_d, calmar=calmar,
                longest_uw=longest_uw, days=days, px=px, rets=rets, rd=dict(zip(days[1:], rets)))

res = {s: stats(v) for s, v in sorted(series.items())}

# equal-weight basket, daily rebalanced vs never rebalanced (hold units)
common = sorted(set.intersection(*[set(r["rd"]) for r in res.values()]))
basket_rets = [sum(res[s]["rd"][d] for s in res) / len(res) for d in common]

def curve_stats(rets, days):
    bal, peak, mdd = 1.0, 1.0, 0.0
    cur_uw_start, longest_uw = days[0], (0, None, None)
    for i, r in enumerate(rets):
        bal *= 1 + r
        if bal >= peak:
            peak = bal
            uw = (days[i] - cur_uw_start).days
            if uw > longest_uw[0]:
                longest_uw = (uw, cur_uw_start, days[i])
            cur_uw_start = days[i]
        mdd = min(mdd, bal / peak - 1)
    uw = (days[-1] - cur_uw_start).days
    if uw > longest_uw[0]:
        longest_uw = (uw, cur_uw_start, None)
    n = len(rets)
    mean_r = sum(rets) / n
    std_r = math.sqrt(sum((r - mean_r) ** 2 for r in rets) / n)
    years = (days[-1] - days[0]).days / 365.25
    cagr = bal ** (1 / years) - 1
    return dict(total=bal - 1, cagr=cagr, sharpe=mean_r / std_r * math.sqrt(365),
                mdd=mdd, calmar=cagr / abs(mdd), longest_uw=longest_uw)

bask = curve_stats(basket_rets, common)

# hold-units basket (no rebalance): 1/3 dollars in each at start
units = {s: (1 / 3) / res[s]["px"][0] for s in res}
hold_days = sorted(set.intersection(*[set(zip(res[s]["days"], res[s]["px"])) and set(res[s]["days"]) for s in res]))
hold_bal = []
for d in hold_days:
    v = sum(units[s] * res[s]["px"][res[s]["days"].index(d)] for s in res)
    hold_bal.append(v)
hold_rets = [hold_bal[i] / hold_bal[i - 1] - 1 for i in range(1, len(hold_bal))]
hold = curve_stats(hold_rets, hold_days[1:])

# pairwise correlations
def corr(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    ca = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return ca / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))

syms = sorted(res)
print("=== Per-asset B&H (2022-04-25 -> 2025-12-31) ===")
for s in syms:
    r = res[s]
    print(f"{s}: total {r['total']*100:+.1f}% | CAGR {r['cagr']*100:+.1f}% | Sharpe {r['sharpe']:.2f} | "
          f"MaxDD {r['mdd']*100:.1f}% (peak {r['peak_d']} -> trough {r['trough_d']}) | Calmar {r['calmar']:.2f} | "
          f"longest underwater {r['longest_uw'][0]}d ({r['longest_uw'][1]} -> {r['longest_uw'][2] or 'STILL'})")
print("\n=== Equal-weight basket, daily rebalanced ===")
print(f"total {bask['total']*100:+.1f}% | CAGR {bask['cagr']*100:+.1f}% | Sharpe {bask['sharpe']:.2f} | "
      f"MaxDD {bask['mdd']*100:.1f}% | Calmar {bask['calmar']:.2f} | longest UW {bask['longest_uw'][0]}d")
print("=== Equal-weight basket, buy-once-hold-units (no rebalance) ===")
print(f"total {hold['total']*100:+.1f}% | CAGR {hold['cagr']*100:+.1f}% | Sharpe {hold['sharpe']:.2f} | "
      f"MaxDD {hold['mdd']*100:.1f}% | Calmar {hold['calmar']:.2f} | longest UW {hold['longest_uw'][0]}d")
print("\n=== Daily-return correlations ===")
for i in range(len(syms)):
    for j in range(i + 1, len(syms)):
        a = [res[syms[i]]["rd"][d] for d in common]
        b = [res[syms[j]]["rd"][d] for d in common]
        print(f"{syms[i]} vs {syms[j]}: {corr(a,b):.3f}")

# worst drawdown episodes per asset (top 3)
print("\n=== Worst drawdown episodes (>20%) per asset ===")
for s in syms:
    r = res[s]
    px, days = r["px"], r["days"]
    peak, peak_d, trough, trough_d, in_dd = px[0], days[0], px[0], days[0], False
    episodes = []
    for i, p in enumerate(px):
        if p >= peak:
            if in_dd and trough / peak - 1 < -0.20:
                episodes.append((trough / peak - 1, peak_d, trough_d, days[i]))
            peak, peak_d, in_dd, trough = p, days[i], False, p
        else:
            in_dd = True
            if p < trough:
                trough, trough_d = p, days[i]
    if in_dd and trough / peak - 1 < -0.20:
        episodes.append((trough / peak - 1, peak_d, trough_d, None))
    episodes.sort()
    for dd_, pd_, td_, rd_ in episodes[:4]:
        print(f"{s}: {dd_*100:.1f}% | peak {pd_} -> trough {td_} -> recovered {rd_ or 'NOT YET'}")
