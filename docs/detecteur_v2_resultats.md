# Détecteur v2 — Résultats (6 novembre 2026)

> Synthèse **agrégée**. Rapport détaillé local : `uv run radar phase0-edge`.

## Ce qui a été accéléré

| Étape | Avant | Après |
|---|---|---|
| Collecte des marchés | ~15 marchés/min | ~50 à 80 marchés/min (parallèle, écriture en flux, mémoire bornée) |
| Profil des wallets | ~2/s | ~15/s |
| Origine des fonds (reçus Polygon, nœud public gratuit) | — | ~27 dépôts/s |
| Rapport Phase 0 | 6 min | ~1 min |
| Étude du détecteur v2 (20 M de lignes) | — | ~3 min, < 2 Go de mémoire |

**Données** : **tous** les marchés géopolitiques résolus et éligibles (2 343 marchés, sans tirage au sort) et les 9 marchés des cas connus, soit **20,7 millions de transactions**. Sont aussi collectés le profil de 14 529 wallets et l'origine de 15 820 dépôts (1 699 financeurs distincts, dont un relais qui finance à lui seul 3 652 comptes).

## La question posée

*« Ce trade gagne-t-il plus souvent que son prix ne le dit ? »*

- **Unité d'analyse** : 45 203 signaux, c'est-à-dire des achats cumulés d'au moins 500 $ d'une issue cotée 50 ¢ ou moins, répartis sur 678 événements.
- **Référence à battre** : le prix payé par un suiveur 5 minutes après le signal, frais compris.
- **Caractéristiques** (toutes connues au moment du signal) :
  - âge et financement du wallet ;
  - flux récent sur l'issue : signaux, comptes neufs, variation du prix, volume ;
  - type de marché ;
  - historique du wallet sur ses marchés déjà résolus ;
  - groupes de comptes partageant le même financeur, en excluant les relais d'exchange.

## Résultats

| Validation | Modèle | Gain de précision sur le prix seul* | Rendement en ne suivant que les signaux où l'avantage prédit dépasse 5 % |
|---|---|---|---|
| Croisée, par événement | linéaire | +0,16 % | +6 % [−2 ; +14] |
| Croisée, par événement | non linéaire | +0,66 % | +14 % [−1 ; +24] |
| **Chronologique** (entraînement avant mai 2026, test après) | linéaire | **−1,18 %** | +6 % [−5 ; +15] |
| **Chronologique** | non linéaire | **−0,79 %** | +6 % [−8 ; +21] |
| Référence : suivre tous les signaux | — | — | **−13 %** [−21 ; −4] |

\* « Gain de précision » = amélioration de la log-loss par rapport au prix du marché seul. Un chiffre positif signifie que le modèle prédit mieux que le prix.

## Lecture

1. **Aucun avantage démontré dans le temps.** Testés sur une période postérieure à leur entraînement, les modèles prédisent *moins bien* que le prix du marché. Les rendements positifs du filtrage (+3 % à +8 %) restent dans le bruit.
2. **Ce qui pèse vraiment, c'est la foule, pas l'initié.** La caractéristique la plus forte est négative : quand de nombreux comptes neufs achètent la même issue dans les 6 heures, elle gagne *moins* souvent que son prix. Suivent :
   - le type de marché (militaire et départ de dirigeant en légère faveur, récompenses en défaveur) ;
   - acheter après une hausse de prix est pénalisé.
   
   Les groupes de comptes (financeur commun) n'apportent presque rien en moyenne. Les vrais réseaux d'initiés sont trop rares pour peser dans une statistique sur 45 000 signaux.
3. **Le seul enseignement robuste est défensif.** Suivre les signaux à l'aveugle perd 13 %. Le filtre évite surtout les outsiders surpayés par la foule, ce qui ramène le résultat autour de zéro.

## Conséquences

- Pas de stratégie automatique de suivi en l'état.
- Le seul vrai test est un **paper trading en conditions réelles** (avant/après), avec un collecteur permanent : un avantage de quelques % ne se démontre qu'avec des mois de données nouvelles.
- **Le radar garde toute sa valeur comme outil d'enquête** : repérer les afflux suspects, les groupes de comptes et la chronologie d'un marché. La décision reste humaine.
- **Pistes plus prometteuses** pour la partie positions :
  - **risque de résolution** sur les quasi-certitudes ;
  - **comptes compétents par catégorie**, évalués dans le temps ;
  - **contre-pied des emballements de comptes neufs** : c'est le signal le plus fort trouvé ici, à confirmer en paper trading.
