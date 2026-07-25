# Jesse — Recherche quantitative & gestion de portefeuille crypto

Projet [Jesse](https://jesse.trade) : recherche systématique de stratégies (backtests, optimisation, Monte Carlo), paper trading, et gestion algorithmique du portefeuille spot familial.

## Organisation du repo

| Dossier / fichier | Contenu |
|---|---|
| `STATE.md` | **Journal de bord vivant** — état de chaque run de recherche, résultats, TODO. Premier fichier à lire pour reprendre le fil. |
| `docs/` | **Documentation** — roadmaps, directives de recherche, références. |
| `reports/` | **Rapports de résultats** — rapports finaux des runs, dossiers de candidats, diagnostics, log complet des backtests (`ALL-RUNS.jsonl`). |
| `strategies/` | **Les stratégies de production uniquement** (l'historique complet reste dans git). |

## Documents clés

- [`docs/R3-PORTFOLIO-ROADMAP.md`](docs/R3-PORTFOLIO-ROADMAP.md) — roadmap de la gestion algorithmique du portefeuille spot (Run #3, en cours)
- [`reports/R2-FINAL-REPORT.md`](reports/R2-FINAL-REPORT.md) — rapport final du Run #2 : les 2 stratégies acceptées (futures, en paper trading sur tclb)
- [`docs/RESEARCH-DIRECTIVE.md`](docs/RESEARCH-DIRECTIVE.md) — la directive des runs de recherche
- [`docs/REJECTED-FAMILIES.md`](docs/REJECTED-FAMILIES.md) — familles de stratégies testées et éliminées (ne pas retester sans idée nouvelle)

## Stratégies en production (paper trading)

| Stratégie | Marché | Sharpe backtest | Statut |
|---|---|---|---|
| `R2_KeltnerAsymmetric` | ETH-USD 4h, Kraken Pro Futures | 1.59 @ 108 trades | ✅ paper trading |
| `R2_KeltnerAsymmetric1h` | ETH-USD 1h, Kraken Pro Futures | 1.56 @ 162 trades | ✅ paper trading |
| `R2_RegimeSwitchETH` | ETH-USD 1h | 1.56 @ 177 trades | alternative (ne pas cumuler avec la 1h) |
| `R2_KeltnerAsymBTC` | BTC-USD 4h | 1.09 @ 97 trades | alternative |

## Lancement

```sh
cp .env.example .env   # puis remplir les clés
cd docker
docker compose up -d
```

Dashboard : [localhost:9000](http://localhost:9000)

⚠️ Le `.env` contient des clés API — il est git-ignoré et ne doit **jamais** être commité.
