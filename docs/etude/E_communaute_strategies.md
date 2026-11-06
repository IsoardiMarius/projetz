# E — Ce que disent les praticiens, et les stratégies de positions (6 novembre 2026)

**Légende** : **[F]** = fait vérifié dans une source primaire ou dans un article de recherche ; **[A]** = affirmation, opinion ou chiffre d'un vendeur, non vérifié.

**Limites** : Reddit et X n'ont pas pu être lus directement. Leurs fils sont cités à travers des relais (Hacker News, presse). Beaucoup de « guides 2026 » sont publiés par des vendeurs de bots.

## 1. Ce que dit la communauté

- **Les bons traders se savent copiés et se cachent.**
  - Ils ouvrent des wallets secondaires et tertiaires et changent de pseudo. Un trader parle de « fuite d'edge » [F, témoignages]. Source : https://news.polymarket.com/p/copytrade-wars (22/09/2025).
  - Un piège classique : le trader suivi revend aux copieurs qui achètent derrière lui [A]. Source : https://news.ycombinator.com/item?id=47091557 (20/02/2026).
- **Un wallet neuf, à lui seul, est un signal faible.**
  - Un financeur commun de type adresse de retrait d'exchange crée de faux clusters [F, méthodologie]. Source : https://docs.bitquery.io/docs/examples/polymarket-api/polymarket-insider-detection-api/
  - Domer, n°1 historique de Polymarket, estime que « 99,9 % » des mouvements suspects ne viennent pas d'initiés [A]. Source : https://www.chinatalk.media/p/prediction-markets-101 (29/07/2025).
  - Des comptes X publient des clusters sans les vérifier [A].
- **Copier un initié arrive trop tard.**
  - Un initié confiant consomme toute la liquidité au bon prix [A].
  - Polymarket a audité en avril 2026 des applications (Polycool, Kreo) qui vendaient l'accès aux comptes initiés présumés [F]. Source : https://www.theblock.co/news/business/2026-04-14-polymarket-audits-startups-potentially-helping-users-copy-insider-trading-report-397387
- **Ce que font les traders des initiés repérés** : ils les copient, ils les contrent (surtout les comptes à PnL négatif [A]), ou ils les signalent à la presse.
- **Qui gagne vraiment** : une étude SSRN sur 588 millions de trades [F] (fil : https://news.ycombinator.com/item?id=48221877, 21/05/2026) montre que :
  - le top 1 % des comptes capte 76,5 % des profits ;
  - ces gagnants sont surtout des fournisseurs de liquidité (ordres limites) ;
  - les performances persistent peu d'un mois sur l'autre ;
  - les initiés n'expliquent pas les plus gros gains.
- **Copier les meilleurs ne marche pas d'un mois sur l'autre.** Le backtest « walk-forward » d'OrcaLayer porte sur ≈ 1,1 million de copies dans le sport.
  - Les meilleurs wallets d'un mois tombent à environ zéro, ou en négatif, le mois suivant.
  - D'un mois sur l'autre, la corrélation des classements va de −0,03 à +0,15.
  - Statut [F] : l'auteur vend un produit, mais son code est public. Source : https://orcalayer.com/blog/polymarket-copy-trading-whales-backtest (10/10/2026).
- **Débats non tranchés** :
  - les initiés rendent-ils les prix plus justes, ou volent-ils de l'information ?
  - faut-il copier tout un compte, ou seulement ses trades dans la catégorie où il est bon ?

## 2. Stratégies au-delà du copy-trading

**Frais** [F] (https://docs.polymarket.com/trading/fees) :
- seuls les takers paient : nombre de parts × taux × p × (1−p), avec un taux de 0,04 à 0,07 selon la catégorie ;
- la géopolitique est sans frais ;
- les makers reçoivent une remise de 15 à 25 %.

| Stratégie | Ce qu'on en sait |
|-----------|------------------|
| Arbitrage intra-marché et neg-risk | ≈ 40 M$ extraits d'avril 2024 à avril 2025 [F] (https://arxiv.org/abs/2508.03474). Seulement 1,12 M$ réellement exécutables compte tenu de la profondeur du carnet ; 10 adresses captent 75 % des gains ; la fenêtre médiane dure 8 à 16 s [F] (https://arxiv.org/pdf/2608.00666). **Réservé aux bots.** |
| Arbitrage entre plateformes | Écart médian d'un demi-cent entre Kalshi et Polymarket sur 2 840 lignes de sport [F] (https://github.com/PDiTO/pm-calibration). Les règles de résolution peuvent différer d'une plateforme à l'autre. |
| Biais favori/outsider | Faible au global (pente de calibration de 1,05). Plus marqué sur les marchés en échelle de seuils (1,23 pour la crypto Polymarket, 1,39 pour la météo Kalshi). Sur la météo, les favoris sont surévalués 1 à 12 h avant la clôture [F] (https://arxiv.org/abs/2610.13593). |
| « Obligations » à 95-99 ¢ | Taux de litige : 1 % au global, 3,4 % en politique, 4,8 % en géopolitique [A] (https://www.polysyncer.com/blog/polymarket-resolution-time-2026). Une perte efface environ 19 gains. 10,5 M$ n'ont pas été payés sur l'« invasion » du Venezuela, faute de correspondre à la définition du marché [F] (https://news.ycombinator.com/item?id=46521773). |
| Market making et récompenses | Témoignage : 10 k$ de capital pour ≈ 200 $ par jour (700-800 $ au pic de 2024) [A] (https://news.polymarket.com/p/automated-market-making-on-polymarket). Récompenses quadratiques selon la proximité du prix [F] (https://docs.polymarket.com/market-makers/liquidity-rewards). Risques : exécution juste avant une nouvelle, « ghost fills » [F] (https://arxiv.org/html/2606.16852v1). |
| Règles de résolution et litiges UMA | Proposants sur liste blanche depuis août 2025 [F]. La lecture fine des règles est souvent citée comme l'avantage le plus accessible à un particulier [A]. |
| News trading | « Plus de 3 s pour réagir, c'est glacialement lent » (Domer) [A]. Les marchés de niche mettraient 10 à 30 min à réagir [A, vendeur]. |
| Météo | Prévisions d'ensemble GFS/ECMWF gratuites (Open-Meteo). La station de résolution est manipulable : CDG en avril 2026, d'où le passage au Bourget [F] (https://www.kpbs.org/news/science-technology/2026/04/23/french-police-probe-suspected-weather-device-tampering-after-odd-polymarket-bet). |
| Sport | Comparer à la cote de Pinnacle, une fois sa marge retirée [A]. Prix quasi identiques à ceux de Kalshi [F]. Copier les wallets sportifs ne marche pas (OrcaLayer). |
| Marchés « mentions » et « tweets » | Fréquences de base calculées sur des transcriptions passées [A]. L'orateur peut manipuler l'issue, comme Brian Armstrong le 30/10/2025 [F] (https://techcrunch.com/2025/11/01/coinbase-ceo-brian-armstrong-trolls-the-prediction-markets). |
| Crypto à court terme | Frais takers depuis le 06/01/2026 [F]. L'arbitrage de latence est considéré comme mort [A]. |

## 3. Outils réutilisables

**Ressources gratuites** :
- le SDK officiel unifié ;
- le jeu de données de Jon Becker (36 Gio en Parquet, Polymarket et Kalshi, licence MIT, https://github.com/Jon-Becker/prediction-market-analysis) ;
- le code de calibration PDiTO ;
- poly-maker (licence MIT, mode papier, https://github.com/warproxxx/poly-maker) ;
- polymarket-insider-tracker (https://github.com/pselamy/polymarket-insider-tracker) ;
- un annuaire d'outils : https://github.com/harish-garg/Awesome-Polymarket-Tools

**Scanners payants** [A] : ArbBets (dès 59 $/mois), Arbitrage Agent (29 $/mois), acteurs Apify (0,05-0,10 $ par scan).

## 4. Pièges

- **Dépôts GitHub piégés** : un bot de copy-trading envoyait la clé privée stockée dans le `.env` via une dépendance npm cachée [F] (https://www.cryptopolitan.com/polymarket-copy-traders-warned/, déc. 2025).
- **Bots Telegram** : Polycule s'est fait voler ≈ 230 k$ [F].
- **La plateforme elle-même** a été attaquée :
  - comptes vidés via un fournisseur d'authentification (déc. 2025) ;
  - phishing de ≈ 3 M$ (06/2026) ;
  - script tiers détourné le 29/10/2026 : 726 wallets vidés, ≈ 3,9 M$ remboursés [F] (https://thehackernews.com/2026/11/hackers-steal-about-27-million-from.html).
- **Fausses preuves de gains** : des vidéos virales montraient des paris fictifs [F] (https://arstechnica.com/tech-policy/2026/06/polymarkets-viral-videos-showed-people-winning-big-but-the-bets-were-fake/).
- **Stratégies mortes ou surcotées** [A] : la latence crypto, l'arbitrage manuel YES+NO, la copie du classement (biais du survivant).

## 5. Pistes classées pour un outil perso

| # | Piste | Intérêt | Difficulté | Données à croiser | Capital modeste ? |
|---|-------|---------|------------|-------------------|-------------------|
| 1 | Évaluer les wallets en walk-forward, par catégorie, nets de frais et de délai | Fort | Moyenne | Trades, résolutions, frais | Oui |
| 2 | Graphe de financement et alerte « wallet neuf ciblé », comme contexte | Fort | Moyenne | Transferts Polygon, horaires des annonces | Oui |
| 3 | Score de risque de résolution pour les quasi-certitudes à 95-99 ¢ | Fort | Moyenne | Texte des règles, historique UMA, catégorie | Oui |
| 4 | Météo : ensembles comparés aux tranches, 1 à 12 h avant la clôture | Fort à moyen | Moyenne | Open-Meteo, station, carnet | Oui, petites tailles |
| 5 | Calibration par catégorie et par horizon | Moyen | Faible | Historique des prix et des résolutions | Oui |
| 6 | Cotes sportives (Pinnacle) et Kalshi comme « juste prix » | Moyen | Moyenne | API de cotes, API Kalshi | Oui |
| 7 | Market making récompensé | Moyen | Élevée | Récompenses, volatilité | Quelques k$, papier d'abord |
| 8 | Arbitrage neg-risk ou entre plateformes | Faible | Élevée | Carnets temps réel | Non |

Pour toutes les pistes qui consistent à prendre des positions (3 à 8), la contrainte légale française s'applique.
