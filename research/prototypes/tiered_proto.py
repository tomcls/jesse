#!/usr/bin/env python3
"""Tiered-exposure defensive overlay screening, DD-first objective.
Signals: S1 = price > SMA200, S2 = EMA50 > EMA200 (computed day N close, applied N+1).
Exposure = f(number of bullish signals). Fees 0.4% on traded fraction.
Reports basket stats + worst episode DDs, plus per-episode comparison vs B&H.
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

def run_tiered(days, px, expo_map, w0=W0, w1=W1, fee=FEE):
    """expo_map: dict {2:e2, 1:e1, 0:e0} exposure per bullish-signal count."""
    e50, e200 = ema_series(px, 50), ema_series(px, 200)
    bal, expo = 1.0, 1.0
    daily = []
    turnover = 0.0
    nswitch = 0
    pending = None
    for i in range(1, len(px)):
        d = days[i]
        r = px[i] / px[i - 1] - 1
        s200 = sma(px, 200, i)
        sig = None
        if s200 is not None:
            sig = (1 if px[i] > s200 else 0) + (1 if e50[i] > e200[i] else 0)
        if d < w0:
            if sig is not None:
                expo = expo_map[sig]
            continue
        if pending is not None and abs(pending - expo) > 1e-9:
            traded = abs(pending - expo)
            bal *= (1 - fee * traded)
            turnover += traded
            nswitch += 1
            expo = pending
        bal *= 1 + expo * r
        pending = expo_map[sig] if sig is not None else expo
        if w0 <= d <= w1:
            daily.append((d, bal, expo))
    return daily, turnover, nswitch

def stats(daily):
    ds = [x[0] for x in daily]
    bs = [x[1] for x in daily]
    rets = [bs[i] / bs[i - 1] - 1 for i in range(1, len(bs))]
    n = len(rets)
    mean_r = sum(rets) / n
    std_r = math.sqrt(sum((x - mean_r) ** 2 for x in rets) / n)
    years = (ds[-1] - ds[0]).days / 365.25
    cagr = (bs[-1] / bs[0]) ** (1 / years) - 1
    peak, mdd = bs[0], 0.0
    for b in bs:
        peak = max(peak, b)
        mdd = min(mdd, b / peak - 1)
    return dict(total=bs[-1] / bs[0] - 1, cagr=cagr,
                sharpe=(mean_r / std_r * math.sqrt(365)) if std_r else 0,
                mdd=mdd, calmar=cagr / abs(mdd) if mdd else float("inf"))

def basket(dailies):
    series = [dict((d, b) for d, b, _ in dl) for dl in dailies]
    common = sorted(set(series[0]) & set(series[1]) & set(series[2]))
    bal, peak, mdd = 1.0, 1.0, 0.0
    out = []
    for i in range(1, len(common)):
        r = sum(sr[common[i]] / sr[common[i - 1]] - 1 for sr in series) / 3
        bal *= 1 + r
        peak = max(peak, bal)
        mdd = min(mdd, bal / peak - 1)
        out.append((common[i], bal, 0))
    return out

# worst episode windows to inspect (from Phase 0)
EPISODES = [("Bear 2022", date(2022, 4, 25), date(2022, 12, 31)),
            ("Correction 2024", date(2024, 3, 11), date(2024, 11, 10)),
            ("Bear 2025 (ETH/SOL)", date(2025, 1, 18), date(2025, 8, 9)),
            ("Chute fin 2025", date(2025, 10, 6), date(2025, 12, 31))]

def episode_dd(daily, a, b):
    seg = [(d, bal) for d, bal, _ in daily if a <= d <= b]
    if not seg:
        return None
    peak, mdd = seg[0][1], 0.0
    for _, v in seg:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    return mdd

CONFIGS = {
    "B&H":              {2: 1.0, 1: 1.0, 0: 1.0},
    "Binaire (0% bear)": {2: 1.0, 1: 1.0, 0: 0.0},
    "100/50/0":          {2: 1.0, 1: 0.5, 0: 0.0},
    "100/50/20":         {2: 1.0, 1: 0.5, 0: 0.2},
    "100/60/25":         {2: 1.0, 1: 0.6, 0: 0.25},
    "100/70/30":         {2: 1.0, 1: 0.7, 0: 0.3},
    "100/50/33 (hodl)":  {2: 1.0, 1: 0.5, 0: 1 / 3},
}

syms = ["BTC", "ETH", "SOL"]
print(f"{'Config':<20} {'Total':>8} {'CAGR':>7} {'Sharpe':>6} {'MaxDD':>7} {'Calmar':>6}  {'Bear22':>7} {'Corr24':>7} {'Bear25':>7} {'Fin25':>7}  {'switches':>8}")
for name, emap in CONFIGS.items():
    dailies, tos, sws = [], 0.0, 0
    for s in syms:
        days = [d for d, _ in raw[s]]
        px = [p for _, p in raw[s]]
        dl, to, sw = run_tiered(days, px, emap)
        dailies.append(dl)
        tos += to
        sws += sw
    bk = basket(dailies)
    st = stats(bk)
    eps = [episode_dd(bk, a, b) for _, a, b in EPISODES]
    eps_s = " ".join(f"{e*100:6.1f}%" if e is not None else "   n/a" for e in eps)
    print(f"{name:<20} {st['total']*100:+7.1f}% {st['cagr']*100:+6.1f}% {st['sharpe']:6.2f} {st['mdd']*100:6.1f}% {st['calmar']:6.2f}  {eps_s}  {sws:8d}")
