# Prototypes Run #3 — scripts et données auditables

**But:** screening rapide des idées de gestion de portefeuille spot (overlay défensif, comité de canaux, frein euphorie, poche stable) AVANT la validation finale dans Jesse. Tout est rejouable: `python3 <script>.py` dans ce dossier.

## Données
`data-binance-daily-closes.csv` — closes journaliers BTC/ETH/SOL-USDT, Binance Perpetual Futures,
extraits de la base Postgres locale (bougies 1m importées, dernier candle de chaque jour) :

```sql
SELECT DISTINCT ON (symbol, to_timestamp(timestamp/1000)::date)
       symbol, to_timestamp(timestamp/1000)::date AS d, close
FROM candle
WHERE exchange='Binance Perpetual Futures' AND symbol IN ('BTC-USDT','ETH-USDT','SOL-USDT')
ORDER BY symbol, to_timestamp(timestamp/1000)::date, timestamp DESC;
```

Continuité vérifiée: BTC 2019-09-09→, ETH 2019-12-02→, SOL 2020-09-21→, **0 jour manquant**.
(Le perp est utilisé comme proxy du spot pour les closes daily; la validation finale se fait sur Binance Spot dans Jesse.)

## Règles de simulation (tous les scripts)
- Signal au close du jour J → exécution à J+1 (aucun lookahead)
- Frais **0.4% par mouvement** (taker Kraken, volontairement pessimiste), sur la fraction tradée
- Long-only, **zéro levier**
- Fenêtre d'évaluation: 2022-04-25 → 2025-12-31. **2026 = holdout, jamais touché.**
- Frein euphorie: percentiles en fenêtre croissante (à chaque date, seul le passé est connu)

## Scripts
- `bh_analysis.py` — benchmark buy-and-hold du panier (Phase 0)
- `regime_proto.py` — screening des 10 filtres de régime + robustesse
- `tiered_proto.py` — exposition graduée + DD par épisode (bear22 / chop24 / bear25 / krach fin25)
- `rotation_proto.py` — lead-lag BTC→alts et rotation force-relative (résultat: rejetée)

## Limites assumées
- Prototypage daily-close: trie les idées, ne remplace pas Jesse (exécution intraday, moteur de frais réel)
- Les briques ont été choisies en voyant la fenêtre entière → un walk-forward du stack complet est requis avant implémentation (TODO en cours)
- ~1.5 cycle de marché disponible: robustesse statistique limitée, irréductible
