# Roadmap — Gestion algorithmique du portefeuille spot (Run #3)

**Date:** 2026-07-25 · **Objectif prioritaire:** plus jamais de drawdown ~-50% sur le portefeuille familial BTC/ETH/SOL, tout en restant exposé (long-only, toujours racheteur). Benchmark = buy-and-hold du panier. Cible: MaxDD ≤ ~-30%, capter l'essentiel de la hausse, turnover minimal (frais + fiscalité).

**Principe de montée en charge:** rien ne touche le compte réel avant la fin du mode ombre. Chaque phase a une porte de sortie (gate) explicite.

---

## Phase A — Recherche & validation (EN COURS)

| # | Tâche | Statut |
|---|---|---|
| A1 | Analyse B&H du panier (DD -72%, corrélations 0.73-0.83, krachs lents) | ✅ fait |
| A2 | Screening filtres de régime + robustesse (35 configs, MaxDD -33..-43% partout) + walk-forward OOS | ✅ fait (prototype Python, données propres vérifiées 0 gap) |
| A3 | Imports candles Binance Spot 1m depuis 2021 (BTC/ETH/SOL-USDT) | 🔄 en cours |
| A4 | **Coupe-circuit anti-flash-crash** (chute depuis pic → réduction immédiate) — attaque le -33/-36% résiduel (janv. 2022, oct. 2025) | ⬜ prochain chantier |
| A5 | Achats sur repli conditionnés au régime (mean reversion intra-tendance — la brique « opportunités ») | ⬜ |
| A6 | Couche allocation: bandes cibles par actif + poche stable, rééquilibrage à seuils, rotation lente vers BTC (signaux mensuels uniquement — le daily a échoué) | ⬜ |
| A7 | Implémentation Jesse (stratégies `R3_*`, mode spot, frais Kraken) + validation complète train/test | ⬜ |
| A8 | **Holdout 2026 — un seul tir**, comme au Run #2 | ⬜ dernière étape recherche |
| A9 | Rapport final de l'étude (« l'étude qui corrige tout ça ») — méthodo, résultats, scénario famille, règles de vie | ⬜ |

**Gate A→B:** stratégie validée OOS + holdout, rapport écrit, paramètres gelés.

## Phase B — Personnalisation & infra de suivi (parallélisable avec A)

| # | Tâche | Qui |
|---|---|---|
| B1 | Clé API Kraken **lecture seule** (Query Funds/Orders) dans `.env` | **Tom** |
| B2 | Snapshot du portefeuille réel + rejeu de la trajectoire familiale exacte (dates/montants d'achat approximatifs) | moi (après B1) |
| B3 | Décision venue d'exécution: exécuteur custom Kraken (recommandé) vs migration vers venue supportée par Jesse live | Tom + moi |
| B4 | Bot Telegram (@BotFather) + notifications natives Jesse sur tclb (trades du paper trading Run #2 en temps réel) | **Tom** (GUI jesse.itcl.io) |
| B5 | Watchdog garde-fous sur tclb: cron 15 min lecture seule → Telegram (seuils DD -16%/-21%, container/websocket morts, résumé quotidien) | moi, **script soumis à approbation avant déploiement** |

**Gate B→C:** clé lecture seule active, Telegram opérationnel.

## Phase C — Mode ombre (4-8 semaines, zéro ordre)

| # | Tâche |
|---|---|
| C1 | Exécuteur spot v0 en mode **signal-only**: chaque jour, lit le portefeuille réel (lecture seule), calcule les cibles d'allocation, journalise les ordres *virtuels* qu'il aurait passés |
| C2 | Alertes Telegram des signaux (« le système serait sorti d'ETH aujourd'hui ») |
| C3 | Comparaison hebdomadaire signaux réels vs backtest (tracking) |

**Gate C→D (critères mesurables):** ≥4 semaines sans bug, signaux conformes au backtest, aucune divergence inexpliquée, et validation humaine de Tom sur le comportement observé.

## Phase D — Live progressif (argent réel)

| # | Tâche |
|---|---|
| D1 | Clé trading **sans droit de retrait** + restriction IP | **Tom** |
| D2 | Garde-fous codés dans l'exécuteur: plafond de turnover jour/semaine, taille d'ordre max, sanity-check prix (écart vs référence → abort), kill-switch fichier, journal complet |
| D3 | Go-live sur **fraction du portefeuille** (~20-30%), montée par paliers après chaque revue mensuelle conforme |
| D4 | Runbook incidents: exchange down, ordre partiellement exécuté, kill-switch, procédure de retour au manuel |

**Gate D→E:** 100% du périmètre décidé par Tom, après ≥2 revues mensuelles conformes.

## Phase E — Gouvernance permanente

| # | Tâche |
|---|---|
| E1 | **Rapport mensuel**: perf vs B&H, état des régimes, dérive d'allocation, frais, et la liste des décisions qui reviennent à Tom (le système exécute la politique; seul Tom change la politique) |
| E2 | Revue trimestrielle des paramètres — jamais de retuning opportuniste sur données récentes; tout changement passe par le process de validation |
| E3 | Kill-switch documenté + test annuel de la procédure d'urgence |
| E4 | Le paper trading futures (Run #2, tclb) suit la même gouvernance mensuelle |

---

## Prochaines actions immédiates

**Moi:** A4 (coupe-circuit), fin des imports A3, puis A5-A6.
**Tom:** B1 (clé lecture seule), B4 (bot Telegram), et si possible les dates/montants d'achat approximatifs de la famille (pour B2).

*Références: `STATE.md` § Run #3 (journal détaillé), mémoire persistante `spot-project`, protocole infra `infra-ia/CLAUDE.md`.*
