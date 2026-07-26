#!/usr/bin/env python3
"""
R3 Spot — Moteur de signaux (mode ombre, Phase C de la roadmap).

Calcule chaque jour l'état de régime et les allocations cibles du portefeuille
spot familial, à partir des données PUBLIQUES Kraken (aucune clé API requise).

Règles (validées — voir reports/R3-ETUDE-FAMILLE.md et STATE.md §R3):
- Par actif: investi si close > SMA200(1D) OU EMA50 > EMA200. Les deux
  baissiers => poche en stable.
- Cibles: 26% du portefeuille par actif investi, >= 22% toujours en stable.
- Rééquilibrage: uniquement si une poche dévie de ±20% de sa cible.
- Zéro levier, long-only, jamais.

Usage:
    python3 executor/signal_engine.py            # état du jour, lisible
    python3 executor/signal_engine.py --json     # sortie machine (pour Telegram/journal)

Mode ombre: ce script NE PASSE AUCUN ORDRE. Il journalise ce que le système
ferait. L'exécution réelle (Phase D) sera un module séparé, avec garde-fous.
"""
import json
import math
import sys
import urllib.request
from datetime import datetime, timezone

PAIRS = {"BTC": "XBTUSD", "ETH": "ETHUSD", "SOL": "SOLUSD"}
ALLOC_PCT = 26.0
BAND_PCT = 20.0
SMA_P, EMA_F, EMA_S = 200, 50, 200


def fetch_daily_closes(pair: str):
    """Kraken public OHLC, interval 1440 = 1D. Returns list of (ts, close), oldest first."""
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=1440"
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.loads(r.read())
    if data.get("error"):
        raise RuntimeError(f"Kraken API error for {pair}: {data['error']}")
    key = [k for k in data["result"] if k != "last"][0]
    rows = data["result"][key]
    return [(int(row[0]), float(row[4])) for row in rows]


def sma(values, n):
    return sum(values[-n:]) / n if len(values) >= n else None


def ema(values, n):
    k = 2 / (n + 1)
    e = values[0]
    for v in values[1:]:
        e = e + k * (v - e)
    return e


def compute_signals():
    out = {"generated_at": datetime.now(timezone.utc).isoformat(), "assets": {}, "targets": {}}
    for asset, pair in PAIRS.items():
        candles = fetch_daily_closes(pair)
        closes = [c for _, c in candles[:-1]]  # drop today's incomplete candle
        last_close = closes[-1]
        s200 = sma(closes, SMA_P)
        e50, e200 = ema(closes, EMA_F), ema(closes, EMA_S)
        if s200 is None:
            raise RuntimeError(f"{asset}: not enough history ({len(closes)} days)")
        cond_sma = last_close > s200
        cond_ema = e50 > e200
        bull = cond_sma or cond_ema
        out["assets"][asset] = {
            "close": last_close,
            "sma200": round(s200, 2),
            "ema50": round(e50, 2),
            "ema200": round(e200, 2),
            "close_gt_sma200": cond_sma,
            "ema50_gt_ema200": cond_ema,
            "regime": "BULL" if bull else "BEAR",
            "days_of_history": len(closes),
        }
        out["targets"][asset] = ALLOC_PCT if bull else 0.0
    out["targets"]["STABLE"] = round(100.0 - sum(out["targets"].values()), 1)
    out["rebalance_band_pct"] = BAND_PCT
    return out


def human(out):
    lines = ["=== R3 Spot — État de régime (mode ombre, aucun ordre passé) ===",
             f"Généré: {out['generated_at']}"]
    for a, d in out["assets"].items():
        lines.append(
            f"{a}: {d['regime']}  (close {d['close']:.0f} {'>' if d['close_gt_sma200'] else '<'} SMA200 {d['sma200']:.0f}; "
            f"EMA50 {'>' if d['ema50_gt_ema200'] else '<'} EMA200)"
        )
    t = out["targets"]
    lines.append("Cibles: " + "  ".join(f"{k} {v:.0f}%" for k, v in t.items()))
    lines.append(f"Rééquilibrage: seulement si une poche dévie de ±{out['rebalance_band_pct']:.0f}% de sa cible.")
    return "\n".join(lines)


if __name__ == "__main__":
    result = compute_signals()
    if "--json" in sys.argv:
        print(json.dumps(result, indent=2))
    else:
        print(human(result))
