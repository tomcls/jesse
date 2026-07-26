# Étude — Protéger et faire fructifier le portefeuille crypto familial

*Version brouillon du 2026-07-26 — sera finalisée après le tir de holdout 2026 et le mode ombre.*

## 1. Ce qui s'est passé (et pourquoi ce n'était pas de votre faute)

La famille a investi ~60 000 € en crypto à partir de 2020, portés par une conviction juste : la crypto est une technologie d'avenir. Le compte a atteint ~120 000 $ au sommet de l'euphorie fin 2021. Puis le marché s'est retourné, personne n'a vendu, et le compte a fondu.

Ce scénario n'est pas une erreur personnelle — c'est le scénario *par défaut* de quiconque détient de la crypto sans règle de sortie. Les chiffres sur 2022-2025 (données Binance vérifiées, zéro jour manquant) :

| Détenir sans règle (buy & hold) | BTC | ETH | SOL | Panier 1/3 |
|---|---|---|---|---|
| Pire chute depuis un sommet | -61% | -67% | **-90%** | **-73%** |
| Temps passé sous l'eau | 588 j | 666 j | 607 j | ~600 j |
| Gain total sur 3.7 ans | +117% | **-1%** | +23% | +77% |

Trois constats :
- **ETH a fait zéro en presque 4 ans**, en passant par -67%. Détenir ne suffit pas.
- Les trois cryptos chutent **ensemble** (corrélations 0.73-0.83) : diversifier entre elles ne protège de rien. La seule protection est de **sortir partiellement du marché**.
- Bonne nouvelle : les grandes chutes sont **lentes** (8-13 mois). Un système a le temps de réagir.

## 2. La solution : trois règles simples

Le système étudié tient en trois phrases :

1. **Jamais tout investi** : au maximum ~78% du capital en crypto (répartis 1/3 BTC, 1/3 ETH, 1/3 SOL), toujours ≥ 22% en réserve stable.
2. **Par crypto : on reste investi tant qu'au moins une des deux tendances de fond est haussière** (prix au-dessus de sa moyenne 200 jours, OU moyenne 50 au-dessus de la moyenne 200). Quand les DEUX deviennent baissières — ce qui n'arrive que dans les vrais hivers — cette crypto est vendue et attend en stable. **Elle est rachetée automatiquement dès qu'une tendance redevient haussière.**
3. **Rééquilibrage à bandes** : si une poche dévie de ±20% de sa cible, on la ramène à la cible (on vend un peu de ce qui a beaucoup monté, on renforce ce qui a baissé).

Aucune prédiction, aucune émotion, ~7 mouvements par an. Zéro levier, jamais.

## 3. Ce que ça aurait donné

**Backtest complet** (moteur Jesse, frais Kraken 0.4%, 2022-04-25 → 2025-12-31) :

| | Système | Buy & hold |
|---|---|---|
| Rendement annuel | **+21 à +27%** ¹ | +16% |
| Pire chute | **≈ -28%** | **-73%** |
| Mouvements | ~7/an | 0 |

¹ +21.1% dans le moteur Jesse (exécution réaliste), +27.3% dans la simulation quotidienne — la vérité est entre les deux.

**Rejoué sur votre histoire** (entrée au pire moment, le sommet de novembre 2021, rapporté à votre compte de 120k$) :

| | Vécu (jamais vendu) | Avec le système |
|---|---|---|
| Point bas | ~18 000 $ (-85%) | ~60 000 $ (-50%) ² |
| Fin 2025 | ~118 000 $ | **~215 000 $** |

² Même le système prend la première jambe d'un krach qui part du sommet — il ne supprime pas le risque, il supprime *les hivers subis*. La différence à l'arrivée vient surtout du **rachat automatique** fin 2022, celui qu'on ne fait jamais soi-même quand on a peur.

## 4. Ce que le système ne fait PAS (à lire attentivement)

- Il ne supprime pas les baisses : **-25 à -30% arrivera** de nouveau. Il supprime les -60/-90%.
- Il ne bat pas le marché chaque année : dans un marché haché sans tendance (comme mi-2024→2025), il coûte ~2-3 points par an — c'est le prix de l'assurance.
- Les chiffres ci-dessus sont des backtests. La règle d'or de nos recherches : en réel, s'attendre à ~60-70% de la performance affichée. Même dégradé, l'écart avec le buy-and-hold reste massif là où ça compte : la pire chute.
- Chaque vente est un événement potentiellement imposable — la basse rotation (~7 ordres/an) limite ce coût.

## 5. Validations effectuées (résumé technique)

- Filtre choisi parmi 10 candidats, robuste sur 35 combinaisons de paramètres (pire cas : DD -43% — toujours 30 points de mieux que le B&H).
- **Walk-forward** : en ne connaissant que 2022→mi-2024, le processus de sélection aurait choisi le même filtre ; sur la période jamais vue (mi-2024→fin 2025), DD -28.5% vs -49% pour le B&H.
- Double implémentation concordante (simulation Python + moteur Jesse, données spot réelles, frais Kraken).
- Idées testées et **rejetées** honnêtement : coupe-circuit de krach (vend les fonds en V), achats sur repli (dégrade le ratio rendement/risque), rotation quotidienne vers BTC (aucun signal), plancher hodl en bear confirmé (aggrave la chute).
- Réserve finale : le test sur 2026 (données jamais utilisées) sera tiré **une seule fois**, à la toute fin, avant le mode ombre.

## 6. Comment ça se déploiera (avec des garde-fous)

1. **Mode ombre (4-8 semaines)** : le système calcule chaque jour ce qu'il *ferait* sur le vrai compte Kraken (lecture seule) et l'envoie sur Telegram. **Aucun ordre réel.** La famille voit le système vivre avant de lui confier quoi que ce soit.
2. **Démarrage progressif** : d'abord ~20-30% du portefeuille, montée par paliers après chaque revue mensuelle conforme.
3. **Garde-fous techniques** : clé API sans droit de retrait, plafonds d'ordres, kill-switch, journal complet de chaque décision.
4. **Rapport mensuel** lisible par tous : ce que le système a fait, pourquoi, et où on en est vs simplement détenir.
5. Ce que le système ne décidera jamais seul : changer ses propres règles. Il exécute la politique ; la famille la possède.

---
*Méthodologie complète : `STATE.md` §R3, prototypes reproductibles dans `research/prototypes/`, backtests dans `reports/ALL-RUNS.jsonl`.*
