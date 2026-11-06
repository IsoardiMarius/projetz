# B — État de l'art : initiés et « smart money » sur Polymarket (6 novembre 2026)

**Légende** : **[V]** = vérifié, par une source primaire ou par plusieurs médias qui concordent ; **[NV]** = non vérifié (source unique, vendeur ou allégation).

## 1. Outils existants

| Outil | Ce qu'il fait et comment | Prix | API |
|-------|--------------------------|------|-----|
| [Bubblemaps](https://www.theblock.co/post/391650/fresh-accounts-netted-1-million-on-polymarket-hours-before-us-airstrikes-on-iran-bubblemaps) | Graphe à bulles : une même couleur regroupe des wallets présumés appartenir à une même entité. Les enquêtes Polymarket sont faites à la main (taille des mises, wallets fraîchement financés, timing). Algorithme non publié. | V2 gratuite ; premium lié au jeton BMT [NV] | Sur devis [NV] |
| Polysights / [Insider Finder](https://gizmodo.com/tracking-insider-trading-on-polymarket-is-turning-into-a-business-of-its-own-2000709286) | Repère les gros trades atypiques de wallets neufs. Seuils non publiés. Revendique « 85 % de signaux gagnants » [NV]. | Freemium | Non trouvée |
| [Unusual Predictions](https://www.bonus.com/prediction-markets/tools/unusual-predictions/) (ex-Hashdive, racheté par Unusual Whales) | Compare chaque trade à l'historique du wallet (z-score). Repère les comptes neufs ou dormants qui misent gros sur un seul marché avant l'événement. Classe la « smart money » par catégorie. | 20 $/mois | Payante |
| [PolyWhaler](https://www.polywhaler.com/) | Note chaque trade de 0 à 100 (taille, cote, timing, contexte) et envoie des alertes Telegram. | 0 à 49 $/mois | ≈ 359 $/an |
| Polymarket Analytics | Classements et profils de traders. | Gratuit | Non trouvée |
| [Arkham](https://info.arkm.com/research/how-to-track-polymarket-whales) | Tableau de bord des marchés de prédiction (PnL, taux de réussite, étiquettes). **Désanonymise** des wallets. | Gratuit | API générique |
| [Nansen](https://docs.nansen.ai/getting-started/credits) | Étiquettes d'entités et filtres Polymarket en ligne de commande. | 49 à 69 $/mois | Oui |
| Bots Telegram (PolyCop, Polycule…) | Copie automatique de trades (≈ 0,5 % de frais par trade [NV]). | — | Polycule piraté : ≈ 230 k$ volés en janv. 2026 [V] |

Polymarket a adopté Chainalysis pour surveiller l'activité on-chain (avril 2026) [V] : https://cointelegraph.com/news/polymarket-chainalysis-insider-betting-detection-prediction-markets

## 2. Le dépôt `vsbtc/polymarket-insider-detection` (code lu, pas exécuté)

**Ce que fait le pipeline** (un seul commit, licence MIT, environ 1 700 lignes de Python) :

1. Repérer un saut du prix du jeton gagnant : au moins +0,15 en 6 h, depuis un prix inférieur ou égal à 0,90.
2. Récupérer les trades d'au moins 1 000 $ via la Data API.
3. Calculer des indicateurs par wallet × marché :
   - prix d'entrée ;
   - part du volume ;
   - pari d'un seul côté ;
   - part achetée avant le saut.
4. Mesurer l'avantage du wallet (`calib_edge`) : taux de réussite moins prix payé. Le compléter par une p-value Poisson-binomiale, en supposant que le prix égale la probabilité.
5. Faire noter par un LLM la « susceptibilité » de chaque marché à l'information privilégiée.
6. Retrouver via Etherscan le premier financeur en USDC, en excluant ceux qui ont financé au moins 50 adresses (exchanges, bridges).
7. Calculer le score final : une somme pondérée, avec des poids fixés à la main.

**Points forts** :
- démarche d'enquête sérieuse ;
- briques réutilisables comme idées : la p-value de « chance » et le filtre des financeurs de masse.

**Limites** :
- **purement rétrospectif** : il faut connaître l'issue et le saut de prix, donc inutilisable en temps réel ;
- poids et seuils arbitraires ;
- aucun test ;
- validation quasi « in-sample » : l'auteur connaissait déjà les cas étudiés ;
- l'hypothèse nulle ignore le biais favori/outsider ;
- angles morts : les trades de moins de 1 000 $ et les financeurs autres que le premier.

## 3. Autres projets open source

| Projet | Apport |
|--------|--------|
| [warproxxx/poly_data](https://github.com/warproxxx/poly_data) (2,3 k★, GPL-3.0) | Collecte on-chain des trades (`OrderFilled`). |
| [ArbitrumFoundation/sybil-detection](https://github.com/ArbitrumFoundation/sybil-detection) | Graphes des transferts et des premiers et derniers financements, découpés en groupes par l'algorithme de Louvain. **Référence pour regrouper des wallets.** |
| [Trusta Labs](https://ethresear.ch/t/trusta-s-ai-and-machine-learning-framework-for-robust-sybil-resistance-in-airdrops/16828) | Détection de communautés, puis affinage par le comportement. |
| [Vedant-29/polymarket-insider-detection](https://github.com/Vedant-29/polymarket-insider-detection) | Âge du wallet, taille, timing, test binomial. Retrouve 3 initiés connus sur 5, avec 4 % de faux positifs. |
| [orcalayer/polymarket-insider-score-backtest](https://github.com/orcalayer/polymarket-insider-score-backtest) | Test pré-enregistré : la méthodologie la plus rigoureuse trouvée. |

## 4. Méthodes documentées

**(a) Trading informé**

- Mitts & Ofir, *From Iran to Taylor Swift: Informed Trading in Prediction Markets* (2026) — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6426778
  - Cinq signaux par wallet × marché : taille relative, taille par rapport aux habitudes, rentabilité, timing, concentration.
  - Test de permutation ; ≈ 143 M$ de profits anormaux.
- Gómez-Cram, Guo, Kung, Jensen, *Prediction Market Accuracy: Crowd Wisdom or Informed Minority?* (2026) — https://ssrn.com/abstract=6617059
- Nechepurenko, *ForesightFlow* (2026) — https://arxiv.org/abs/2605.00493
- PIN, Easley et al. (1996) — https://doi.org/10.1111/j.1540-6261.1996.tb04074.x
- VPIN, Easley, López de Prado, O'Hara (2012) — https://doi.org/10.1093/rfs/hhs053
- Rendements anormaux avant une annonce :
  - Meulbroek (1992) — https://doi.org/10.1111/j.1540-6261.1992.tb04679.x
  - Augustin et al. (2019) — https://doi.org/10.1287/mnsc.2018.3122
- Chance ou compétence :
  - Kosowski et al. (2006) — https://doi.org/10.1111/j.1540-6261.2006.01015.x
  - Barras, Scaillet, Wermers (2010), contrôle des fausses découvertes (FDR) — https://doi.org/10.1111/j.1540-6261.2009.01527.x
  - Gneiting & Raftery (2007) — https://doi.org/10.1198/016214506000001437
- Biais favori/outsider :
  - Snowberg & Wolfers (2010) — https://doi.org/10.1086/655844
  - Bürgi, Deng, Whelan (2025), sur Kalshi — https://www.ucd.ie/economics/t4media/WP2025_19.pdf

**(b) Regrouper les wallets d'une même entité**

- Victor (2020), heuristiques de regroupement d'adresses Ethereum — https://doi.org/10.1007/978-3-030-51280-4_33
- Actions synchronisées :
  - SynchroTrap (2014) — https://doi.org/10.1145/2660267.2660269
  - CopyCatch (2013) — https://doi.org/10.1145/2488388.2488400
- Sirolly et al., détection du wash trading sur Polymarket — https://business.columbia.edu/faculty/research/network-based-detection-wash-trading
- ARTEMIS (2024) — https://doi.org/10.1145/3589334.3645597

**(c) Anomalies et communautés dans les graphes**

- Louvain (2008) — https://arxiv.org/abs/0803.0476
- Leiden (2019) — https://doi.org/10.1038/s41598-019-41695-z
- FRAUDAR (2016), résistant aux leurres — https://doi.org/10.1145/2939672.2939747
- Elliptic (2019) — https://arxiv.org/abs/1908.02591
- Elliptic2 (2024) — https://arxiv.org/abs/2404.19109
- Synthèse : Akoglu et al. (2015) — https://doi.org/10.1007/s10618-014-0365-y

## 5. Cas publics 2024-2026

| Cas | Signaux observés | Suites |
|-----|------------------|--------|
| Élection américaine 2024 (« Théo ») | 4 comptes ; sondages privés fondés sur l'« effet voisin ». **Informé, pas initié.** [Source](https://www.theblock.co/post/324996/french-polymarket-whale-us-election-profit-france-ban) | Aucune manipulation selon Polymarket |
| AlphaRaccoon (Google Year in Search, déc. 2025) | 22 paris gagnés sur 23 ; compte ancien | **Inculpé** par le DOJ et la CFTC le 27/05/2026, ≈ 1,2 M$ [V] [Source](https://www.cftc.gov/PressRoom/PressReleases/9237-26) |
| Nobel de la paix 2025 | Cote de 3,75 % à 73 % en une nuit ; compte récent | Enquête en cours [V] [Source](https://blockworks.co/news/polymarket-nobel-probe) |
| Maduro (3/01/2026) | Compte créé vers le 26/12 ; 13 paris ; 33 k$ misés pour 410 k$ gagnés ; retrait le jour même | **Inculpé** [V] [Source](https://www.justice.gov/opa/pr/us-soldier-charged-using-classified-information-profit-prediction-market-bets) |
| Israël (févr. 2026) | Un réserviste et un civil | **Inculpés** [V] [Source](https://www.nbcnews.com/world/israel/israel-charges-reservist-classified-information-bet-polymarket-rcna258709) |
| Frappes sur l'Iran (28/02/2026) | 6 wallets créés et financés moins de 24 h avant ; achats à 10-20 ¢ ; ≈ 1 M$ de gains [V] | Aucune poursuite connue |
| 9 comptes liés à l'Iran (mai 2026) | 98 % de réussite sur plus de 80 paris ; 2,4 M$ ; pertes « leurres » présumées [NV] [Source](https://www.cbsnews.com/news/betting-on-iran-war-insider-trading-concerns-prediction-markets-60-minutes/) | Aucune poursuite connue |
| Rapport ACDC (août 2026) | 152 comptes ; 8 M$ ; 97 % de réussite. La moitié a fait un premier pari sur un outsider moins de 2 jours après l'ouverture du compte. [Source](https://finance.yahoo.com/markets/crypto/articles/polymarket-faces-fresh-insider-trading-133446085.html) | Renvois au DOJ [NV] |
| Kalshi | Détection interne grâce à la vérification d'identité (KYC). [Source](https://www.yogonet.com/international/news/2026/02/26/117792-kalshi-suspends-mrbeast-editor-and-former-california-candidate-in-insider-trading-cases) | Amendes, suspensions [V] |

## 6. Le copy-trading est-il rentable ?

- **Aucune étude indépendante ne mesure le rendement net d'un copieur.**
- **Les comptes compétents existent, mais le PnL ne permet pas de les trouver.** 3,14 % des comptes sont compétents et 44 % le restent dans le temps. Pourtant, le PnL ne recoupe la compétence qu'à 12 % [NV, résumé de presse]. [Source](https://www.theblock.co/post/398902/skilled-polymarket-traders-are-a-3-minority-and-everyone-else-funds-their-gains-study)
- **Un initié fait bouger le prix 7 à 12 fois plus par dollar qu'un trader compétent.**
- **L'avantage des meilleurs comptes est mince et rapide.** Un test pré-enregistré sur les 10 % meilleurs wallets trouve +0,83 ¢ par part à 24 h, gagnés surtout dans la première heure, soit +1,17 ¢ par entrée nets de frais. Un copieur n'obtient pas leur prix d'entrée. [Source](https://dev.to/ekocam/we-pre-registered-a-polymarket-insider-score-it-passed-and-we-still-didnt-ship-it-55aj)
- **Dans les cas publics, la détection est venue trop tard** : après l'annonce, ou après que la cote a été multipliée par 20.
- **Les takers perdent en moyenne** (ceux qui achètent au prix affiché) : environ 32 % sur Kalshi (Bürgi et al.).

## Signaux les plus utiles, classés par valeur

1. Achat à bas prix de l'issue gagnante peu avant qu'elle ne soit révélée, sur un marché dont l'issue est connue en secret par un petit groupe. Validé (Maduro).
2. Compte neuf, ou financé juste avant le pari. Validé.
3. Historique de gains improbable une fois ajusté aux cotes : test Poisson-binomial, permutations, contrôle des fausses découvertes (FDR). Validé (AlphaRaccoon).
4. Concentration sur un seul marché ou un seul thème. Validé.
5. Marché à secret : militaire, nominations, prix. Les outsiders militaires gagnent 52 % du temps, contre 14 % en politique (ACDC).
6. Taille anormale par rapport à la liquidité et aux habitudes du wallet (Mitts & Ofir).
7. Sortie rapide ou effacement des traces : revente à 90 ¢ ou plus, retrait, changement de pseudo. Validé.
8. Financement commun par un wallet personnel, précédé d'un petit transfert test. Allégué.
9. Comptes neufs synchronisés sur la même issue. Allégué.
10. Paris d'un seul côté, avec de petites pertes qui servent de leurre. Allégué.
