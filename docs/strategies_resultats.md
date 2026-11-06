# Trois stratégies testées sur l'historique — Résultats (6 novembre 2026)

> Synthèse agrégée. Rapport local : `uv run radar phase0-strategies`.
> Données : les 2 343 marchés géopolitiques résolus entre octobre 2025 et octobre 2026 (20 M de transactions), soit 207 548 positions simulées.
> Règles communes : mise de 1 $, achat au marché 5 min après le déclencheur, frais compris, position gardée jusqu'à la résolution. Entre crochets : intervalle de confiance à 90 %. Une stratégie solide doit gagner **avant et après** mai 2026.

## 1. Contre-pied de l'emballement des comptes neufs

On achète l'issue opposée quand beaucoup de comptes neufs se ruent sur la même issue en 6 h.

| Variante | Positions | Rendement par $ | Avant mai 2026 | Après mai 2026 |
|---|---|---|---|---|
| Contre-pied de n'importe quel signal (référence) | 9 739 | −0 % [−3 ; +2] | −2 % | +6 % |
| ≥ 3 comptes neufs | 237 | +3 % [−4 ; +13] | +2 % | +10 % |
| ≥ 5 comptes neufs | 83 | +11 % [0 ; +23] | +12 % | **−17 %** |
| ≥ 10 comptes neufs | 18 (6 événements) | +25 % [+5 ; +37] | +25 % | aucun cas |

**Verdict : piste intéressante, mais non prouvée.** Les emballements forts sont rares (moins de 100 cas par an) et le résultat s'inverse d'une période à l'autre. Seul un suivi en direct sur plusieurs mois permettrait de trancher.

## 2. Quasi-certitudes (90-99 ¢)

On achète une issue dès qu'elle atteint une tranche de prix élevée.

| Tranche | Positions | Gagnantes | Prix payé | Rendement par $ | Annualisé | Avant / après mai |
|---|---|---|---|---|---|---|
| 90-95 ¢ | 1 561 | 88,4 % | 92,5 % | −4 % [−6 ; −3] | −69 % | −4 % / −6 % |
| 95-97 ¢ | 1 614 | 93,1 % | 96,0 % | −3 % [−4 ; −2] | −59 % | −2 % / −5 % |
| 97-99 ¢ | 1 767 | 95,6 % | 97,5 % | −2 % [−3 ; −1] | −44 % | −1 % / −4 % |
| ≥ 99 ¢ | 1 770 | 98,2 % | 99,0 % | −1 % [−1 ; 0] | −29 % | 0 % / −3 % |

**Verdict : perdant, de façon nette et stable.** Les quasi-certitudes perdent un peu plus souvent que leur prix ne l'annonce, sur toutes les tranches et sur les deux périodes. Les marchés à résolution ambiguë ne sont pas comptés, ce qui avantage même la stratégie : la réalité est donc au moins aussi mauvaise.

## 3. Copier les comptes compétents

On copie les positions des wallets dont l'historique bat nettement les prix payés. Cet historique est mesuré uniquement sur des marchés déjà résolus au moment de la copie.

| Variante | Positions | Rendement par $ | Avant mai 2026 | Après mai 2026 |
|---|---|---|---|---|
| Copier tout le monde (référence) | 137 067 | −4 % [−6 ; −2] | −4 % | −4 % |
| Comptes à mauvais historique | 11 984 | −3 % | −2 % | −4 % |
| Historique ≥ 10 positions, très bon (z ≥ 2) | 7 115 | −2 % [−4 ; +1] | 0 % | −4 % |
| Historique ≥ 20 positions, exceptionnel (z ≥ 3) | 1 252 | −1 % [−5 ; +3] | −3 % | +5 % |

**Verdict : perdant.** Un bon historique ne se prolonge pas assez pour couvrir les coûts de la copie. C'est cohérent avec les études publiées.

## Conclusion

| Stratégie | Résultat |
|---|---|
| Copier les initiés présumés (Phase 0) | Perdant |
| Détecteur v2 | Ne bat pas le prix du marché |
| Contre-pied de l'emballement | Piste à surveiller en direct, non prouvée |
| Quasi-certitudes | Perdant, de façon stable |
| Comptes compétents | Perdant |

Sur les marchés géopolitiques, **les données publiques ne donnent pas d'avantage facile** : le prix intègre déjà ce qu'on voit des autres parieurs.
