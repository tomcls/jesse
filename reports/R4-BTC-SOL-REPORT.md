# Research Run #4 — Rapport du matin : stratégies BTC & SOL perpetual

**Nuit du 2026-07-25 → 26**, mission de Tom avant coucher : « une stratégie BTC (Sharpe ~1.5) et une SOL, perpetual long+short, rendement ≥ 20%/an, DD max ≤ 25% (dur), Sharpe secondaire. Backtester sur toute la période en DB (2022 → juillet 2026). »

**Résultat : les deux trouvées, critères durs dépassés avec marge.** 31 backtests loggés cette nuit (`reports/ALL-RUNS.jsonl`).

## Les deux candidates (configs figées dans les fichiers)

| | `R4_BTCKeltnerAsym` | `R4_SOLTrendFollow` |
|---|---|---|
| Marché | BTC-USD **1h**, Kraken Pro Futures | SOL-USD **4h**, Kraken Pro Futures |
| Mécanisme | Keltner asymétrique (long 4.4 / short 6.8), gate volatilité, sortie mi-canal | Trend-following EMA 12/44 + trailing stop ATR×5.0 à cliquet |
| **Sharpe** | **1.5701** | **1.3221** |
| **Rendement annuel** | **+36.7%** | **+42.3%** |
| **Max DD** | **-14.5%** ✓ | **-18.6%** ✓ |
| Profit factor | 2.09 | 2.09 |
| Trades (4.2 ans) | 130 (~2.6/mois) | 107 (~2.1/mois) |
| Backtest | `a5fb2199-d76c-45c2-b02a-d440c177d752` | `fa9eb6d7-c17f-4d88-a732-a559e0db632a` |

## Corrélations (règle dédup < 0.3) — portefeuille réellement diversifié

| | R4_SOL | R2_ETH_1h | R2_ETH_4h |
|---|---|---|---|
| **R4_BTC** | -0.03 | 0.06 | 0.07 |
| **R4_SOL** | — | 0.01 | -0.01 |

Les 4 stratégies (2 en paper trading + ces 2 nouvelles) sont quasi orthogonales — chaque paire < 0.16.

## Robustesse observée

- **BTC** : colline lisse — période 64 nette (48/56/80 tous inférieurs), long 4.2→1.53 / 4.4→1.57, zone short 6.2-6.8 → 1.48-1.57. Découverte : couper presque totalement les shorts (7.4) **double le DD** (-24.5% vs -14.5%) — les shorts rares sont une assurance-krach, ne pas les désactiver.
- **SOL** : voisinage EMA sain (12/44→1.32, 13/48→1.26, 14/52 aux critères), zone trail 4.5-5.5 toute conforme. **⚠️ trail ≤ 4.0 s'effondre (0.47) — ne jamais serrer le trailing sous 4.5.** La famille Keltner a d'abord été essayée sur SOL et plafonne à 0.54 (rejetée, cohérent avec le Run #2) ; c'est le pivot vers le trend-following qui a débloqué.

## ⚠️ Limites honnêtes — à lire avant de déployer

1. **Pas de holdout.** Sur instruction explicite de Tom, la fenêtre inclut 2026 : il ne reste **aucune donnée vierge** pour un test final. Les configs ont été *sélectionnées* sur la totalité de la fenêtre → l'estimation est optimiste par construction. **Le paper trading est donc le vrai test hors-échantillon** — comme pour le Run #2, attendre une dégradation vers ~60-70% du Sharpe de backtest en réel.
2. **Une nuit de recherche**, pas le protocole complet du Run #2 : pas de split train/test discipliné, pas de Monte Carlo, pas de cross-venue. Ces validations peuvent être ajoutées avant tout passage en réel (recommandé si on dépasse le paper trading).
3. Jesse ne modélise pas le funding des perps ; frais taker 0.05% inclus.
4. SOL à risk_percent 2.5 : plus agressif que le reste du portefeuille — c'est ce qui atteint les +20%/an demandés, mais c'est le premier paramètre à baisser si le paper trading déçoit.

## Recommandation

Déployer les deux en **paper trading** sur tclb à côté des deux R2 (4 stratégies, corrélations quasi nulles), surveiller 4-8 semaines avec les mêmes seuils d'alerte relatifs (DD backtest × 1.5 : alerte à **-22%** pour BTC, **-28%** pour SOL), puis décider.

*Généré automatiquement pendant la nuit — chaque backtest est dans `ALL-RUNS.jsonl`, chaque étape dans `STATE.md` §R4.*
