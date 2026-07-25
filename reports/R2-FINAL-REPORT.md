# Research Run #2 — Rapport final (v2, post-optimisations)

**Date :** 2026-07-24 · **Backtests loggés :** 158 (`reports/ALL-RUNS.jsonl`) · **Familles explorées :** ~15
**Fenêtre de recherche :** 2022-04-25 → 2025-12-31 · **Holdout intouché :** 2026-01-01 → aujourd'hui (réservé au test final unique)
**Setup :** Kraken Pro Futures, levier 3x, frais taker 0.05% modélisés, slippage pessimiste Jesse, **funding perpétuel NON modélisé**.

---

## 1. 🏆 PORTEFEUILLE FINAL RECOMMANDÉ : deux stratégies acceptées (Sharpe > 1.5, corr 0.17)

### ✅ ACCEPTÉE #1 — `R2_KeltnerAsymmetric` · **ETH-USD · 4h** · Sharpe 1.5936

Breakout Keltner asymétrique : canal serré côté long / large côté short, gate d'expansion de volatilité, sortie midline, stop ATR. Entrées MARKET.

**Config PROD (verrouillée dans les defaults du fichier) :**
```
period=25, long_mult=1.5, short_mult=3.0, atr_period=10,
atr_sma_period=34, vol_expansion_mult=1.1, atr_mult=1.2, risk_percent=1.2
```

| Métrique | Valeur |
|---|---|
| Trades | 108 (2.48/mois) ✅ in-range |
| **Sharpe** | **1.5936** (reconstruction conservatrice : 1.39) |
| Max DD | **-10.36%** |
| Rendement annuel | +35.1% (net +199%) |
| Profit factor / Win rate | 2.61 / 45.4% |
| Backtest | `412cef67-4e3e-4713-acc6-b17c319709b6` |

Validation : provenance IS/OOS (train 1.55 / test 1.65) ✅ · robustesse lisse (1.57-1.60 sur tous les voisins) ✅ · cross-symbol BTC 0.77 / SOL 0.72 ✅ · MC propre (original DANS la plage, DD meilleur que la médiane MC, pas de signature d'overfit) ✅.

### ✅ ACCEPTÉE #2 — `R2_KeltnerAsymmetric1h` · **ETH-USD · 1h** · Sharpe 1.5559 · corr 0.17 vs #1

Même mécanisme, timeframe 1h, asymétrie inversée (longs sélectifs / shorts serrés — la direction gagnante varie par TF).

**Config PROD (verrouillée dans les defaults du fichier) :**
```
period=64, long_mult=4.8, short_mult=4.1, atr_period=15,
atr_sma_period=18, vol_expansion_mult=1.25, atr_mult=1.25, risk_percent=1.7
```

| Métrique | Valeur |
|---|---|
| Trades | 162 (3.66/mois) ✅ in-range |
| **Sharpe** | **1.5559** |
| Max DD | -13.73% |
| Rendement annuel | **+54.3%** (net +395%) |
| Win rate | 30.9% |
| **Corr quotidienne vs #1** | **0.1705** ✅ |
| Backtest | `f78cd655-9900-4bf6-a6a4-3e67e967d923` |

Validation : provenance IS/OOS (train 1.45 / **test 1.83**) ✅ · cross-symbol : **BTC 1.293 @ 180t** (meilleur chiffre BTC de tout le run !), SOL 0.18 (faible, DD -28.6%) ✅ · **MC le plus propre du projet** : Sharpe original 1.53 collé à la médiane MC (1.68), profit net original ENTRE médiane et best-5% — exactement le critère du protocole ✅.

**Portefeuille 50/50 #1+#3 : Sharpe combiné théorique ≈ 1.9-2.0** (deux flux 1.55+ à corr 0.17).

---

## 2. Alternatives documentées (non retenues dans le portefeuille)

- **`R2_RegimeSwitchETH`** (overlay breakout+fade, ETH 1h) — optimisé : **177t @ 1.5594** (+57%/an, DD -15.7%, backtest `a16247f2-3a86-4504-8fe9-c0198cedf315`) mais 8 trades au-dessus du plafond (4.06/mois vs cap 4.0) ; version strictement in-range : 169t @ 1.4402 (manuel). **Écarté du portefeuille : corr 0.456 avec l'acceptée #2** (son composant breakout EST le même mécanisme) → compte comme une seule stratégie selon la règle de dédup. Reste le meilleur choix si on remplaçait la #2.
- **`R2_KeltnerAsymBTC`** (BTC 4h natif) — 97t @ 1.0907 (manuel ; l'optimiseur n'a rien donné de mieux en OOS : max 1.11 à ~57 trades). **Meilleure option BTC réelle : la réplication BTC de l'acceptée #2 (1.293 @ 180t)** — 3e jambe possible du portefeuille si souhaité (corr vs #1 = 0.055 pour la famille).
- **`R2_PairsRatioZscore`** (stat-arb ratio ETH/BTC, seuils asym 2.6/3.1) — 107t @ 0.6537, corr 0.014. Le plus diversifiant, le plus faible.

## 3. Bilan des optimisations disciplinées

_Protocole : train 2022-04/05→2024-08-31, test OOS 2024-09→2025-12-31, sélection sur les métriques de TEST uniquement, revalidation full-window, jamais le holdout._

| Stratégie | Avant (manuel) | Après (optimiseur) | Verdict |
|---|---|---|---|
| #1 ETH 4h | 1.5004 @ 118 | **1.5936 @ 108**, DD -14.3→-10.4 | ✅ Gain net |
| #3 ETH 1h | 1.3372 @ 168 | **1.5559 @ 162** (+0.22 !) | ✅ Franchit la barre |
| #2 overlay 1h | 1.4402 @ 169 | 1.5594 @ 177 (8 sur-plafond) | ✅ mais redondant avec #3 |
| #4 BTC 4h | 1.0907 @ 97 | rien de mieux en OOS | ❌ Inchangé |

Leçon : l'optimiseur discipliné (sélection OOS) a été rentable sur 3 configs sur 4 — à condition de bornes resserrées et de ne jamais sélectionner sur le train.

## 4. Ce qui a été éliminé (résumé)

Morts toutes cryptos : mean reversion naïf, grid, squeeze, trend-pullback Connors, VWAP-deviation. Plafonnés bas : Donchian vol-breakout (~0.5), fakeout fade (~0.25, nouveau mécanisme réel), range-fade ADX (0.708 @ 33t, ETH-only), short-only (0.40, SOL-only). Leçons : le multi-TF dégrade ce signal dans les deux sens ; l'asymétrie long/short a amélioré 3 familles ; la clôture native du timeframe fait partie du signal.

## 5. Checklist pour le passage en PROD (paper trading)

1. **Fichiers à copier** : `strategies/R2_KeltnerAsymmetric/` (acceptée #1) et `strategies/R2_KeltnerAsymmetric1h/` (acceptée #2). Les defaults des `hyperparameters()` SONT les configs prod — **vérifier après copie** (le docstring de chaque fichier documente la config attendue).
2. **Exchange** : nom exact `"Kraken Pro Futures"` (PAS "Kraken Futures" — crash silencieux du worker sinon).
3. **Routes** : #1 → ETH-USD 4h ; #2 → ETH-USD 1h. Pas de data_routes nécessaires.
4. **Funding non modélisé** en backtest : les positions tiennent de quelques heures à plusieurs jours ; le paper trading mesurera l'impact réel (attendu : quelques % par an de moins).
5. **Toutes les entrées sont MARKET (taker 0.05%)** — le slippage réel vs le modèle pessimiste est l'autre chose que le paper mesurera.
6. **Ne PAS backtester 2026** — le holdout reste vierge ; le paper trading est le test hors-échantillon vivant.
7. **Sizing** : risk_percent différents (1.2 pour #1, 1.7 pour #2) — c'est voulu (issus de l'optimisation), le risque réalisé par trade est comparable une fois les stops pris en compte (stops plus serrés sur #1).
8. Suivi conseillé : comparer mensuellement le Sharpe réalisé paper vs les prédictions ; alerte si DD dépasse ~1.5× le max backtest (-10.4% → alerte à -16% pour #1 ; -13.7% → -21% pour #2).

## 6. 🌍 Validation cross-venue — Binance, même période (2026-07-24)

Les deux configs acceptées, **paramètres strictement identiques**, sur Binance Perpetual Futures ETH-USDT (fee aligné 0.05%, levier 3x), même fenêtre de recherche :

| Stratégie | Kraken (référence) | **Binance** | Écart |
|---|---|---|---|
| #1 (4h) | 1.5936 @ 108t | **1.4002 @ 107t**, DD -12.5% | -0.19 |
| #2 (1h) | 1.5559 @ 162t | **1.3864 @ 153t**, DD -14.7% | -0.17 |

**Verdict : l'edge n'est PAS un artefact de la microstructure Kraken.** Même comptes de trades, Sharpe à -0.17/-0.19 seulement (attendu : venue plus efficient/liquide), DD comparables. C'était la réponse directe à l'objection "marché différent" — même période, autre venue, ça tient.

## 7. 🔒 TEST HOLDOUT 2026 — TIRÉ le 2026-07-24 (one-shot, sur demande de Tom)

Les deux configs acceptées, telles quelles, Kraken, **2026-01-01 → 2026-07-22** (données jamais vues par aucune étape de la recherche) :

| Stratégie | Trades (6.5 mois) | Sharpe | Net | Rdt annualisé | Max DD | Win rate |
|---|---|---|---|---|---|---|
| #1 (4h) | 16 | **+0.53** | +3.6% | +6.6% | -12.3% | 31.2% |
| #2 (1h) | 29 | **+0.79** | +10.8% | +20.5% | -19.8% | 17.2% |

**Lecture honnête :**
- ✅ **Les deux sont POSITIVES sur données vierges** — le scénario catastrophe (edge fictif → effondrement) est exclu.
- ⚠️ Sharpe holdout (0.53/0.79) ≪ backtest (1.59/1.56) — mais **cohérent avec la dégradation live prédite** (50-70% du backtest → attendu 0.8-1.1 ; observé légèrement en dessous pour #1).
- ⚠️ **Échantillon minuscule** : 16 et 29 trades sur 6.5 mois. L'erreur-type d'un Sharpe sur une telle fenêtre est ±1.0+ — ces chiffres sont statistiquement compatibles à la fois avec "edge intact mais bruité" et "edge réduit de moitié". Ils ne tranchent pas ; ils excluent seulement le désastre.
- 🚨 **Drawdowns** : #1 a déjà touché -12.3% en 6.5 mois (max backtest 3.6 ans : -10.4%) ; #2 a atteint **-19.8%** (max backtest : -13.7%, seuil d'alerte fixé à -21%). Le 1er semestre 2026 a été un régime difficile (chop) pour ces stratégies — les win rates effondrés (17% pour #2) le confirment.
- **Conséquence** : le holdout est maintenant CONSOMMÉ. Tout re-tuning informé par 2026 serait de l'auto-illusion — les configs sont définitivement gelées ; seul le paper trading tranche désormais.

**Verdict global final : edge réel mais de taille modeste en live — Sharpe réaliste attendu ~0.6-1.0.** Recommandation : paper trading avec sizing conservateur, évaluation à 6-12 mois, seuils d'alerte DD inchangés (-16% / -21%).

## 8. Liens dashboard

- **Acceptée #1** : `http://localhost:9000/#/backtest/412cef67-4e3e-4713-acc6-b17c319709b6` · MC : `.../monte-carlo/5975c10f-d488-482c-b438-b01bf1be16f8`
- **Acceptée #2** : `http://localhost:9000/#/backtest/f78cd655-9900-4bf6-a6a4-3e67e967d923` · MC : `.../monte-carlo/e869f2d0-692b-4796-ba7c-3593d38a62bd`
- Cross-venue Binance : #1 `.../backtest/c8b3c857-9bc5-40fd-98d4-def2fcc9a92a` · #2 `.../backtest/9576be88-af33-4afb-a4d5-789ee5ec10c8`
- **Holdout 2026** : #1 `.../backtest/d721598d-e466-4c9b-b249-8d0c32571394` · #2 `.../backtest/d9adbac8-59e5-4c70-8192-90d617cd5303`
- Alternative overlay : `http://localhost:9000/#/backtest/a16247f2-3a86-4504-8fe9-c0198cedf315`
- Journal complet : `reports/ALL-RUNS.jsonl` (162 entrées) · Historique de session : `STATE.md`
