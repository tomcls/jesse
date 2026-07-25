#!/usr/bin/env python3
"""(1) Lead-lag measurement between BTC/ETH/SOL daily returns.
(2) Rotation overlay: per-sleeve, if own regime bull AND ratio-vs-BTC strong -> asset;
    bull but ratio weak -> BTC; bear -> stable. Compare vs binary winner & B&H.
Window 2022-04-25 -> 2025-12-31, fees 0.4% on traded fraction, signal J -> exec J+1.
"""
import csv, math
from collections import defaultdict
from datetime import date

PATH = "data-binance-daily-closes.csv"
W0, W1 = date(2022, 4, 25), date(2025, 12, 31)
FEE = 0.004

raw = defaultdict(dict)
with open(PATH) as f:
    for sym, d, close in csv.reader(f):
        raw[sym.replace("-USDT", "")][date.fromisoformat(d)] = float(close)

common = sorted(set(raw["BTC"]) & set(raw["ETH"]) & set(raw["SOL"]))
days = common
px = {s: [raw[s][d] for d in days] for s in ["BTC", "ETH", "SOL"]}
rets = {s: [px[s][i] / px[s][i - 1] - 1 for i in range(1, len(days))] for s in px}

def corr(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)

print("=== Lead-lag: corr( BTC ret[t], ALT ret[t+k] ) — k>0 means BTC leads ===")
for alt in ["ETH", "SOL"]:
    line = []
    for k in range(-3, 4):
        if k >= 0:
            a, b = rets["BTC"][:len(rets["BTC"]) - k or None], rets[alt][k:]
        else:
            a, b = rets["BTC"][-k:], rets[alt][:len(rets[alt]) + k]
        line.append(f"k={k:+d}:{corr(a,b):.3f}")
    print(f"BTC->{alt}: " + "  ".join(line))

print("\n=== Ratio trends (persistence of relative strength, weekly) ===")
for alt in ["ETH", "SOL"]:
    ratio = [raw[alt][d] / raw["BTC"][d] for d in days]
    wk = [ratio[i] / ratio[i - 7] - 1 for i in range(7, len(ratio), 7)]
    ac = corr(wk[:-1], wk[1:])
    print(f"{alt}/BTC weekly ratio-change autocorr(1): {ac:.3f}  (>0 = trend persists)")

def sma(arr, n, i):
    return sum(arr[i - n + 1:i + 1]) / n if i >= n - 1 else None

def ema_series(arr, n):
    k = 2 / (n + 1)
    out = [arr[0]]
    for p in arr[1:]:
        out.append(out[-1] + k * (p - out[-1]))
    return out

e50 = {s: ema_series(px[s], 50) for s in px}
e200 = {s: ema_series(px[s], 200) for s in px}
ratios = {s: [px[s][i] / px["BTC"][i] for i in range(len(days))] for s in ["ETH", "SOL"]}

def regime_bull(s, i):
    s200 = sma(px[s], 200, i)
    if s200 is None:
        return None
    return px[s][i] > s200 or e50[s][i] > e200[s][i]  # the validated combined filter

def ratio_strong(s, i, n=90):
    if s == "BTC":
        return True
    r = sma(ratios[s], n, i)
    return None if r is None else ratios[s][i] > r

def run_portfolio(target_fn):
    """target_fn(i) -> dict asset->weight (+ 'CASH'). Executed J+1. Returns daily balances."""
    bal = 1.0
    w = {"BTC": 1 / 3, "ETH": 1 / 3, "SOL": 1 / 3, "CASH": 0.0}
    pending = None
    daily = []
    switches, turnover = 0, 0.0
    for i in range(1, len(days)):
        d = days[i]
        if d < W0:
            t = target_fn(i)
            if t is not None:
                w = t
            continue
        if pending is not None:
            delta = sum(abs(pending[k] - w[k]) for k in w) / 2
            if delta > 0.001:
                bal *= (1 - FEE * delta * 2)  # sell + buy legs
                turnover += delta
                switches += 1
            w = pending
        day_r = sum(w[s] * (px[s][i] / px[s][i - 1] - 1) for s in ["BTC", "ETH", "SOL"])
        bal *= 1 + day_r
        t = target_fn(i)
        pending = t if t is not None else w
        if W0 <= d <= W1:
            daily.append((d, bal))
    return daily, switches, turnover

def stats(daily):
    bs = [b for _, b in daily]
    ds = [d for d, _ in daily]
    rr = [bs[i] / bs[i - 1] - 1 for i in range(1, len(bs))]
    n = len(rr)
    mr = sum(rr) / n
    sd = math.sqrt(sum((x - mr) ** 2 for x in rr) / n)
    years = (ds[-1] - ds[0]).days / 365.25
    cagr = (bs[-1] / bs[0]) ** (1 / years) - 1
    peak, mdd = bs[0], 0.0
    for b in bs:
        peak = max(peak, b)
        mdd = min(mdd, b / peak - 1)
    return dict(total=bs[-1] / bs[0] - 1, cagr=cagr, sharpe=mr / sd * math.sqrt(365),
                mdd=mdd, calmar=cagr / abs(mdd))

def t_bh(i):
    return {"BTC": 1 / 3, "ETH": 1 / 3, "SOL": 1 / 3, "CASH": 0.0}

def t_binary(i):
    w = {"BTC": 0.0, "ETH": 0.0, "SOL": 0.0, "CASH": 0.0}
    for s in ["BTC", "ETH", "SOL"]:
        rb = regime_bull(s, i)
        if rb is None:
            return None
        w[s] = 1 / 3 if rb else 0.0
    w["CASH"] = 1 - sum(w.values())
    return w

def t_rotation(i):
    w = {"BTC": 0.0, "ETH": 0.0, "SOL": 0.0, "CASH": 0.0}
    rb_btc = regime_bull("BTC", i)
    if rb_btc is None:
        return None
    for s in ["BTC", "ETH", "SOL"]:
        rb = regime_bull(s, i)
        if rb is None:
            return None
        rs = ratio_strong(s, i)
        if rs is None:
            return None
        if rb and rs:
            w[s] += 1 / 3          # sleeve in its own asset
        elif rb and not rs and rb_btc:
            w["BTC"] += 1 / 3      # weak vs BTC -> reallocate sleeve to BTC
        elif rb and not rs:
            w["CASH"] += 1 / 3     # weak vs BTC and BTC itself bearish -> stable
        # bear -> stable
    w["CASH"] = 1 - (w["BTC"] + w["ETH"] + w["SOL"])
    return w

def t_rotation_nofilter(i):
    """rotation only (no regime filter) — isolates the allocation effect"""
    w = {"BTC": 0.0, "ETH": 0.0, "SOL": 0.0, "CASH": 0.0}
    for s in ["BTC", "ETH", "SOL"]:
        rs = ratio_strong(s, i)
        if rs is None:
            return None
        if rs:
            w[s] += 1 / 3
        else:
            w["BTC"] += 1 / 3
    return w

print("\n=== Portfolio variants (EW basket, fees 0.4%/side on traded fraction) ===")
print(f"{'Variant':<26} {'Total':>8} {'CAGR':>7} {'Sharpe':>6} {'MaxDD':>7} {'Calmar':>6} {'switch':>6} {'turnover':>8}")
for name, fn in [("B&H", t_bh), ("Regime binaire (ref)", t_binary),
                 ("Rotation seule (no filtre)", t_rotation_nofilter),
                 ("Regime + rotation BTC", t_rotation)]:
    dl, sw, to = run_portfolio(fn)
    st = stats(dl)
    print(f"{name:<26} {st['total']*100:+7.1f}% {st['cagr']*100:+6.1f}% {st['sharpe']:6.2f} "
          f"{st['mdd']*100:6.1f}% {st['calmar']:6.2f} {sw:6d} {to:7.1f}x")
