#!/usr/bin/env python3
"""Phase 1 screening: long-only defensive regime filters on daily closes.
Data: Bybit USDT perp daily closes (proxy for spot; 2020/2021+ for MA warmup).
Evaluation window: 2022-04-25 -> 2025-12-31. Fees: 0.4%/side (Kraken taker, conservative).
Signals computed on day N close, executed on day N+1 close (no lookahead).
"""
import csv, math
from collections import defaultdict
from datetime import date

PATH = "data-binance-daily-closes.csv"
W0, W1 = date(2022, 4, 25), date(2025, 12, 31)
FEE = 0.004

raw = defaultdict(list)
with open(PATH) as f:
    for sym, d, close in csv.reader(f):
        raw[sym.replace("-USDT", "")].append((date.fromisoformat(d), float(close)))
for s in raw:
    raw[s].sort()

def sma(px, n, i):
    return sum(px[i - n + 1:i + 1]) / n if i >= n - 1 else None

def ema_series(px, n):
    k = 2 / (n + 1)
    out = [px[0]]
    for p in px[1:]:
        out.append(out[-1] + k * (p - out[-1]))
    return out

def run_filter(days, px, signal, w0=W0, w1=W1, fee=FEE):
    """signal(i) -> True=invested. Executed next day. Returns stats in window."""
    bal, invested = 1.0, True  # start invested (Tom already holds)
    daily = []  # (day, balance)
    trades = 0
    pending = None
    for i in range(1, len(px)):
        d = days[i]
        r = px[i] / px[i - 1] - 1
        if d < w0:
            # warmup zone: just track desired state without fees
            s = signal(i - 1)
            if s is not None:
                invested = s
            continue
        if pending is not None and pending != invested:
            bal *= (1 - fee)
            invested = pending
            trades += 1
        if invested:
            bal *= 1 + r
        s = signal(i)
        pending = s if s is not None else invested
        if w0 <= d <= w1:
            daily.append((d, bal, invested))
    ds = [x[0] for x in daily]
    bs = [x[1] for x in daily]
    rets = [bs[i] / bs[i - 1] - 1 for i in range(1, len(bs))]
    n = len(rets)
    mean_r = sum(rets) / n
    std_r = math.sqrt(sum((x - mean_r) ** 2 for x in rets) / n)
    years = (ds[-1] - ds[0]).days / 365.25
    total = bs[-1] / bs[0] - 1
    cagr = (bs[-1] / bs[0]) ** (1 / years) - 1
    peak, mdd = bs[0], 0.0
    for b in bs:
        peak = max(peak, b)
        mdd = min(mdd, b / peak - 1)
    tim = sum(1 for x in daily if x[2]) / len(daily)
    return dict(total=total, cagr=cagr, sharpe=(mean_r / std_r * math.sqrt(365)) if std_r else 0,
                mdd=mdd, calmar=cagr / abs(mdd) if mdd else float("inf"),
                trades=trades, tim=tim, daily=daily)

def fmt(name, r):
    return (f"{name:<28} total {r['total']*100:+7.1f}% | CAGR {r['cagr']*100:+6.1f}% | Sharpe {r['sharpe']:5.2f} | "
            f"MaxDD {r['mdd']*100:6.1f}% | Calmar {r['calmar']:5.2f} | trades {r['trades']:3d} | in-mkt {r['tim']*100:3.0f}%")

results = {}
for sym in ["BTC", "ETH", "SOL"]:
    days = [d for d, _ in raw[sym]]
    px = [p for _, p in raw[sym]]
    emas = {n: ema_series(px, n) for n in (20, 50, 100, 200)}

    filters = {}
    filters["B&H"] = lambda i: True
    for n in (100, 150, 200):
        filters[f"SMA{n} in/out"] = (lambda n: lambda i: (px[i] > s if (s := sma(px, n, i)) else None))(n)
    # hysteresis: exit only if < SMA*(1-b), enter only if > SMA*(1+b)
    def hyst(n, b):
        state = {"in": True}
        def sig(i):
            s = sma(px, n, i)
            if s is None:
                return None
            if state["in"] and px[i] < s * (1 - b):
                state["in"] = False
            elif not state["in"] and px[i] > s * (1 + b):
                state["in"] = True
            return state["in"]
        return sig
    filters["SMA200 hyst 3%"] = hyst(200, 0.03)
    filters["SMA150 hyst 3%"] = hyst(150, 0.03)
    filters["SMA100 hyst 5%"] = hyst(100, 0.05)
    filters["EMA50>EMA200 cross"] = lambda i: emas[50][i] > emas[200][i]
    filters["EMA20>EMA100 cross"] = lambda i: emas[20][i] > emas[100][i]
    # dual condition: price>SMA200 OR EMA50>EMA200 (stay unless both bearish)
    filters["SMA200 OR goldcross"] = lambda i: ((px[i] > s) if (s := sma(px, 200, i)) else None) or emas[50][i] > emas[200][i]
    # both must be bullish
    filters["SMA200 AND goldcross"] = lambda i: ((px[i] > s) if (s := sma(px, 200, i)) else None) and emas[50][i] > emas[200][i]

    print(f"\n===== {sym} =====")
    for name, f in filters.items():
        r = run_filter(days, px, f)
        results[(sym, name)] = r
        print(fmt(name, r))

# Basket view for selected filters: equal weight across the 3 assets, daily rebalanced
print("\n===== EW BASKET (1/3 each, daily rebal) =====")
names = ["B&H", "SMA200 in/out", "SMA150 in/out", "SMA200 hyst 3%", "SMA150 hyst 3%",
         "EMA50>EMA200 cross", "EMA20>EMA100 cross", "SMA200 OR goldcross", "SMA200 AND goldcross", "SMA100 hyst 5%"]
for name in names:
    series = [dict((d, b) for d, b, _ in results[(s, name)]["daily"]) for s in ["BTC", "ETH", "SOL"]]
    common = sorted(set(series[0]) & set(series[1]) & set(series[2]))
    rets = []
    for i in range(1, len(common)):
        r = sum(series[j][common[i]] / series[j][common[i - 1]] - 1 for j in range(3)) / 3
        rets.append(r)
    bal, peak, mdd, bs = 1.0, 1.0, 0.0, [1.0]
    for r in rets:
        bal *= 1 + r
        bs.append(bal)
        peak = max(peak, bal)
        mdd = min(mdd, bal / peak - 1)
    n = len(rets)
    mean_r = sum(rets) / n
    std_r = math.sqrt(sum((x - mean_r) ** 2 for x in rets) / n)
    years = (common[-1] - common[0]).days / 365.25
    cagr = bal ** (1 / years) - 1
    tr = sum(results[(s, name)]["trades"] for s in ["BTC", "ETH", "SOL"])
    print(f"{name:<28} total {(bal-1)*100:+7.1f}% | CAGR {cagr*100:+6.1f}% | Sharpe {mean_r/std_r*math.sqrt(365):5.2f} | "
          f"MaxDD {mdd*100:6.1f}% | Calmar {cagr/abs(mdd):5.2f} | trades {tr:3d}")
