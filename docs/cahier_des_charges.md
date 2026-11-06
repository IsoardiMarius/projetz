# Cahier des charges — Outil personnel d'analyse Polymarket

> **Version 0.1** (brouillon à discuter), 6 novembre 2026.
> Établi à partir d'une étude en cinq volets : technique, état de l'art, sources de données, juridique, communauté et stratégies. Les rapports complets, avec leurs sources, sont dans [`etude/`](etude/).
> Nom de code provisoire : **Radar**.

---

## 0. En bref

**Radar** est un outil personnel qui observe Polymarket en temps réel. Il a quatre fonctions :

1. Il repère les **flux informés**, c'est-à-dire les comptes qui parient comme s'ils savaient.
2. Il **cartographie les liens** entre comptes sous forme de bulles.
3. Il **croise** ces informations avec d'autres données : actualités, autres marchés, données alternatives.
4. Il **aide à décider** d'une position et **mesure, avant de risquer de l'argent**, si une stratégie aurait rapporté.

**Trois constats de l'étude changent la façon de construire :**

1. **Depuis la France, on ne peut pas prendre de position sur Polymarket dans les règles.** L'ANJ bloque le site depuis juillet 2026. Le site et l'API d'ordres sont en « close-only » : on peut fermer une position, pas en ouvrir. Les CGU interdisent le VPN. En revanche, observer, analyser et faire du **paper trading** (positions simulées) reste possible (§ 2.1).
2. **Les données sont excellentes et gratuites.**
   - Un flux temps réel global donne tous les trades avec l'adresse du wallet.
   - L'historique complet de chaque marché est accessible.
   - Les dépôts et retraits sont traçables, mais la traçabilité s'arrête souvent sur des « hubs » (§ 2.2).
3. **L'avantage disparaît vite.**
   - Le prix réagit dans l'heure au trade d'un initié, et dans les cas célèbres la détection publique est venue *après* l'annonce.
   - Copier les meilleurs comptes du classement ne marche pas d'un mois sur l'autre.

   La question décisive n'est donc pas « qui est initié ? », mais **« reste-t-il un avantage quand je le vois ? »**. On la mesure en premier, avant de construire la partie positions (Phase 0, § 3). D'autres pistes de positions, comme le risque de résolution ou la météo, pourraient être plus rentables (§ 6.3).

---

## 1. Objectifs et limites

### Usages visés

| # | Usage | Description |
|---|-------|-------------|
| U1 | Détection | Repérer en temps réel, et a posteriori, les trades et comptes au comportement « informé », avec les preuves qui justifient chaque signal. |
| U2 | Cartographie | Graphe à bulles des comptes et de leurs liens (financement, transferts, trades synchronisés), regroupés en clusters. |
| U3 | Croisement | Confronter les trades à l'actualité horodatée, aux autres marchés et à des données alternatives. |
| U4 | Décision | Fiche de décision pour chaque signal, suivi de comptes jugés fiables, autres stratégies de positions (§ 6). |
| U5 | Vérification | Backtests et paper trading pour mesurer, sans risquer d'argent, ce qu'une stratégie aurait rapporté. |

### Ce que l'outil ne fera pas

- **Contourner le géoblocage** : pas de VPN, pas de proxy pour passer des ordres.
- **Identifier les personnes** derrière les wallets : pas de rattachement à un nom, un compte X ou une étiquette Arkham pour des particuliers.
- **Publier** des listes de comptes ou des scores.
- **Exécuter des ordres automatiquement** dans les premières versions.

---

## 2. Ce que l'étude a établi

### 2.1 Cadre juridique (hypothèse : tu résides en France, à confirmer)

| Sujet | Constat | Conséquence pour le projet |
|-------|---------|----------------------------|
| Accès à Polymarket | Site illégal selon l'ANJ (févr. 2026), bloqué par les FAI (juill. 2026). CGU : France = juridiction restreinte, VPN interdit, compte en « close-only » ou résilié en cas d'infraction. L'API d'ordres est elle aussi en close-only pour la France. | **Pas de prise de position réelle depuis la France.** Le module « positions » fonctionne en **paper trading**. Il passera en réel seulement si ta situation le permet légalement (résidence hors de France, évolution du droit). |
| Joueur | Aucun texte trouvé qui sanctionne le joueur lui-même. Les risques sont pratiques : fonds bloqués, aucun recours. | À faire valider par un avocat avant toute mise réelle. |
| Polymarket US, Kalshi | Réservés aux résidents américains. | Pas d'alternative équivalente depuis la France. |
| Copier des positions publiques | Côté US, le copieur « pur » ne paraît pas exposé : un trade on-chain est une information publique. Tout contact ou partage de gains avec le compte copié change l'analyse. MAR et MiCA ne paraissent pas s'appliquer. | Pas de problème pour l'outil. Aucun contact avec les comptes suivis. |
| Utilisation des API | Les CGU interdisent le scraping (§ 4.2), mais les API sont publiques et documentées. | Zone grise : utiliser uniquement les API officielles, respecter les limites de débit, s'identifier par un User-Agent clair. |
| RGPD | Un usage strictement personnel et local relève plausiblement de l'exemption domestique. Elle tombe dès qu'on publie, partage ou rattache des identités. | Données en local, aucun résultat dans le dépôt Git (qui est public), aucune désanonymisation. |
| AI Act | Un score fondé sur des faits de marché objectifs, appliqué à des wallets pseudonymes, paraît hors de l'interdiction de l'art. 5.1.d. | Présenter le score comme un **signal de marché** (« flux informé »), jamais comme un « détecteur de délinquants ». La décision reste humaine. |
| Fiscalité | Qualification incertaine : gain de jeu non imposable, plus-value sur actifs numériques (art. 150 VH bis) ou BNC. Formulaire 3916-bis obligatoire pour les comptes étrangers. | Sans objet tant qu'on reste en paper trading. |

### 2.2 Données disponibles (vérifiées par des tests le 6/11/2026)

| Besoin | Source | État |
|--------|--------|------|
| Tous les trades en temps réel, avec le wallet | RTDS `wss://ws-live-data.polymarket.com` (topic `activity`) | Fonctionne, sans clé, reçu en moins d'1 s. **Non documenté officiellement** : il faut prévoir un repli. |
| Repli temps réel / suivi d'un wallet | Data API v2 `/v2/trades`, `/v2/activity` (interrogation régulière) | Décalage d'environ 2 s. Cache CDN de 5 min sur les URL identiques, à contourner par un paramètre variable. |
| Historique complet d'un marché | `/v2/trades?condition=…` | Complet : 82 000 trades en 29 s, recoupé à 99,999 % avec le volume officiel. |
| Prix et carnet en direct | WebSocket CLOB `market`, `/book` | Fonctionne. **Aucun historique officiel du carnet** : il faut l'enregistrer nous-mêmes dès le départ. |
| Métadonnées des marchés, résolutions, litiges | Gamma `/markets`, Data API `/v2/resolutions` | Fonctionne. |
| Dépôts et retraits | `/v2/activity` (DEPOSIT/WITHDRAWAL) + reçus de transaction Polygon | Fonctionne, avec des limites détaillées ci-dessous. |
| Historique SQL et premier financeur | Dune (`polymarket_polygon.*`) | Payant (≈ 75 $/mois), en option. |

**Pièges techniques identifiés :**
- **Traçabilité des dépôts** : la source d'un dépôt est souvent un **hub** (relais d'exchange ou de bridge, des millions de transactions) au-delà duquel on ne peut plus remonter. Le graphe de financement doit donc **détecter et neutraliser les hubs** : un financeur commun « Binance » ne prouve rien.
- **Fausses lignes DEPOSIT** : certaines sont en réalité des distributions groupées de récompenses, à exclure.
- **Changements de contrats** : migration du 28/04/2026 (collatéral USDC.e → pUSD, nouveaux contrats d'échange, nouveau type de wallet). Le modèle de données doit être robuste à ces changements.
- **Nœuds RPC gratuits** : très bridés. Il faudra un RPC avec clé gratuite, ou l'API Etherscan v2 (gratuite).
- **Cloudflare** rejette le User-Agent Python par défaut.

### 2.3 État de l'art

- **Outils existants** :
  - Bubblemaps (enquêtes manuelles) ;
  - Unusual Predictions, ex-Hashdive (20 $/mois) ;
  - PolyWhaler (score par trade, 0 à 49 $/mois) ;
  - Polysights ;
  - Arkham et Nansen (labels).

  Aucun ne publie sa méthode de façon vérifiable. Leurs performances revendiquées (« 85 % de signaux gagnants ») ne sont pas vérifiées.
- **Polymarket lui-même** surveille avec Chainalysis depuis avril 2026. Les initiés grossiers seront de plus en plus vite repérés et bannis.
- **Méthodes académiques de référence** :
  - Mitts & Ofir (2026), *Informed Trading in Prediction Markets* : cinq signaux par paire wallet × marché, test de permutation ;
  - Gómez-Cram et al. (2026) ;
  - tests « chance ou compétence » avec contrôle du taux de fausses découvertes (FDR) ;
  - clustering de Sybil (Arbitrum, Louvain/Leiden), FRAUDAR (résistant aux leurres).
- **Code réutilisable** :
  - `vsbtc/polymarket-insider-detection` : bonne conception, mais rétrospectif et sans tests. On reprend les idées, pas le code ;
  - `ArbitrumFoundation/sybil-detection` ;
  - `warproxxx/poly_data` (licence GPL : s'en inspirer plutôt qu'en copier le code).
- **Copy-trading** : aucune étude indépendante de sa rentabilité nette.
  - Un test pré-enregistré trouve **+0,83 ¢ par part à 24 h pour les 10 % meilleurs wallets**, obtenu surtout dans la première heure, et que le copieur ne capte pas entièrement.
  - Les initiés font bouger le prix 7 à 12 fois plus que les traders simplement compétents.
  - Le bot Telegram de copy-trading Polycule a été piraté (≈ 230 k$ volés).

### 2.4 Ce que disent les praticiens

- **Les bons traders se savent copiés et se cachent** : ils ouvrent des wallets secondaires et changent de pseudo (newsletter officielle de Polymarket, sept. 2025). Le clustering sert donc aussi à suivre les traders compétents, pas seulement les initiés.
- **Copier le classement ne marche pas d'un mois à l'autre.** Un backtest « walk-forward » sur environ 1,1 million de copies dans le sport le montre : les meilleurs wallets d'un mois tombent à zéro ou en négatif le mois suivant. La corrélation des classements d'un mois sur l'autre va de −0,03 à +0,15.
- **Qui gagne vraiment** (étude SSRN sur 588 millions de trades) :
  - le top 1 % des comptes capte 76,5 % des profits ;
  - ces gagnants sont surtout des **fournisseurs de liquidité** (ordres limites) ;
  - les initiés n'expliquent pas les plus gros gains.
- **Un wallet neuf, à lui seul, est un signal faible.**
  - Un financeur commun de type exchange crée de faux clusters.
  - Domer, n°1 historique de Polymarket, estime que la quasi-totalité des mouvements « suspects » ne viennent pas d'initiés.
- **Frais** :
  - seuls les « takers » paient (ceux qui achètent au prix affiché et prennent la liquidité) ;
  - **la géopolitique est sans frais** ;
  - les « makers » reçoivent 15 à 25 % de remise (ceux qui posent des ordres limites et fournissent la liquidité).
- **Sécurité** : de nombreux pièges ciblent les traders.
  - Un dépôt GitHub de copy-trading volait les clés privées.
  - Le bot Telegram Polycule a été vidé de 230 k$.
  - Polymarket lui-même a été piraté trois fois en un an, dont 726 wallets vidés le 29/10/2026.

---

## 3. Versions et périmètre

| Version | Contenu | Critère pour passer à la suite |
|---------|---------|--------------------------------|
| **Phase 0 — Étude de données** | Notebooks sur 4 à 6 cas connus (Maduro, Iran 28/02, Nobel 2025, Google Year in Search, cessez-le-feu d'avril 2026, plus des marchés témoins). Calcul des signaux. Mesure de **l'avantage restant après X minutes**. | Les signaux auraient-ils repéré ces comptes **avant** l'annonce ? Restait-il un avantage net de frais et de slippage ? → décide de l'ambition de la partie « positions ». |
| **V1 — Socle et interface basique** | Collecte (temps réel et historique), stockage, profil de compte avec PnL, fiche marché, graphe à bulles, signaux a posteriori. | L'interface permet de refaire en quelques clics l'analyse d'un cas connu. |
| **V2 — Temps réel et paper trading** | Radar en direct, alertes, enregistrement des carnets, fiche de décision, paper trading réaliste. | Paper trading sur plusieurs semaines, avec un journal de performance. |
| **V3 — Croisements avancés** | Actualité horodatée (RSS, Telegram, X, GDELT), cotes Kalshi, ADS-B militaire, modèle de score calibré, autres stratégies. | Gain mesuré de chaque nouvelle source sur les performances. |
| **Plus tard** | Exécution semi-automatique, **seulement si le cadre légal le permet**. | — |

---

## 4. Exigences fonctionnelles

Priorités : **M** = indispensable, **S** = souhaitable, **C** = si le temps le permet.

### Collecte et stockage

| ID | Exigence | Prio | Version |
|----|----------|------|---------|
| F-01 | Ingérer le flux temps réel de tous les trades (RTDS), avec un repli automatique par interrogation de `/v2/trades` si le flux tombe. | M | V1 |
| F-02 | Récupérer l'historique complet de n'importe quel marché ou wallet à la demande. | M | V1 |
| F-03 | Enregistrer en continu le carnet d'ordres des marchés suivis, pour simuler le slippage. | M | V2 |
| F-04 | Collecter les métadonnées des marchés (catégorie, règles, dates, résolution, litiges). | M | V1 |
| F-05 | Tracer les dépôts et retraits jusqu'au premier financeur, et détecter les hubs (exchanges, bridges, relais). | M | V1 |
| F-06 | Filtrer ce qu'on stocke : tout pour les catégories surveillées, rien pour le bruit (marchés crypto de 15 min, par exemple). Le filtre est configurable. | M | V1 |
| F-07 | Ingestion idempotente (aucun doublon), horodatage UTC, conservation de la source de chaque donnée. | M | V1 |

### Analyse

| ID | Exigence | Prio | Version |
|----|----------|------|---------|
| F-10 | Reconstituer les positions et le PnL réalisé et latent par wallet, et les comparer aux chiffres de l'API. | M | V1 |
| F-11 | Calculer les signaux du § 5 au niveau trade, position, wallet, cluster et marché. | M | V1 |
| F-12 | Construire le graphe des liens, en distinguant les liens **observés** des liens **inférés**, et détecter les communautés. | M | V1 |
| F-13 | Tester « chance ou compétence » avec correction du biais favori/outsider et du multi-test. | M | V1 |
| F-14 | Calculer des markouts : performance d'un trade à +5 min, +1 h et +24 h. | M | V1 |
| F-15 | Recalculer les scores en temps réel à chaque trade pertinent. | M | V2 |
| F-16 | Rejouer l'historique (backtest) sans biais d'anticipation : à la date T, n'utiliser que ce qui était connu à T. | M | Phase 0 / V2 |

### Décision

| ID | Exigence | Prio | Version |
|----|----------|------|---------|
| F-20 | Fiche de décision pour chaque signal (§ 6). | M | V2 |
| F-21 | Liste de comptes suivis (« fiables »), avec l'historique de leur fiabilité. | M | V1 |
| F-22 | Paper trading : exécution simulée sur le carnet enregistré, frais réels, journal et statistiques. | M | V2 |
| F-23 | Alertes (navigateur ou e-mail ; messagerie à décider). | S | V2 |
| F-24 | Autres stratégies de positions (§ 6.3). | S | V3 |

### Croisements

| ID | Exigence | Prio | Version |
|----|----------|------|---------|
| F-30 | Timeline d'événements publics horodatés, en saisie manuelle puis en collecte automatique (RSS officiels, Telegram, GDELT, X). | M (manuel) / S (auto) | V1 / V3 |
| F-31 | Cotes d'autres marchés (Kalshi) pour repérer les écarts. | S | V3 |
| F-32 | Données alternatives : avions militaires (adsb.lol), NOTAM, anomalies thermiques (NASA FIRMS). | C | V3 |

---

## 5. L'algorithme de détection

### 5.1 Principes

1. **Chaque signal est explicable** : il pointe vers les faits qui le déclenchent (hash de transaction, horodatage, prix, source).
2. **Pas de poids fixés à la main sans validation.** Chaque signal est d'abord converti en une mesure statistique interprétable (p-value, percentile). Les signaux sont ensuite combinés par un modèle **calibré sur des cas réels**. Les poids sont appris, puis vérifiés hors échantillon.
3. **Pas d'anticipation** : un score calculé à la date T n'utilise que des informations disponibles à T.
4. **Le bon niveau d'agrégation** :
   - les marchés d'un même événement (« frappe avant le 28/02 », « avant le 1/03 », « avant le 15/03 ») sont **corrélés**. Les compter comme des paris indépendants gonflerait artificiellement la significativité. On agrège donc **par événement** ;
   - les initiés se répartissent sur plusieurs wallets, d'où un score **par cluster**.

### 5.2 Les signaux

Classés par valeur selon l'étude. « Validé » signifie observé dans un cas qui a donné lieu à des poursuites.

| # | Signal | Calcul | Statut |
|---|--------|--------|--------|
| S1 | Achat à bas prix de l'issue gagnante peu avant qu'elle ne devienne publique | Part de la mise achetée à une cote ≤ 20-30 % dans les heures ou jours qui précèdent le moment où l'info devient publique. Ce moment est estimé automatiquement par le saut de prix (+15 points en 6 h), puis affiné par l'horodatage de l'actualité. | Validé (Maduro) |
| S2 | Compte neuf ou financé juste avant le pari | Délai entre création ou premier dépôt et premier pari ; délai entre un dépôt et une grosse mise. | Validé |
| S3 | Gains improbables une fois ajustés aux cotes | p-value Poisson-binomiale avec probabilité **corrigée du biais favori/outsider** (courbe de calibration estimée sur tous les marchés résolus), agrégée par événement ; contrôle du taux de fausses découvertes (FDR, Benjamini-Hochberg) sur l'ensemble des wallets. | Validé (AlphaRaccoon) |
| S4 | Concentration | Part de l'activité sur un seul événement ou un seul thème (indice de Herfindahl). | Validé |
| S5 | Marché « à secret » | Marché dont l'issue est connue d'un petit groupe à l'avance (militaire, nominations, prix, décisions d'entreprises). Étiquette par catégorie, à affiner à la main. Selon un rapport, les outsiders gagnent 52 % du temps sur les marchés militaires contre 14 % en politique. | Validé |
| S6 | Taille anormale | Mise rapportée à la liquidité du marché (carnet, volume) **et** aux habitudes du wallet. | Publié (Mitts & Ofir) |
| S7 | Markouts positifs | Le prix évolue durablement dans le sens du trade après coup. Mesurable **avant** la résolution, donc utile en temps réel. | Méthode standard de détection du flux informé |
| S8 | Sortie rapide ou effacement | Revente à 90 ¢ ou plus avant la résolution, retrait juste après, changement de pseudonyme. | Validé |
| S9 | Financement commun | Même premier financeur (hors hubs), petit « transfert test » avant la mise, transfert direct ou TIP entre comptes. | Allégué |
| S10 | Synchronisation | Plusieurs comptes neufs qui achètent la même issue à quelques minutes d'intervalle, avec des montants proches. | Allégué |
| S11 | Leurres | Paris d'un seul côté, avec de petites pertes qui semblent servir de camouflage. | Allégué |

### 5.3 Graphe et clusters

**Nœuds** : wallets. Taille de la bulle au choix : mise, PnL ou volume. Couleur : cluster.

**Arêtes typées, avec un poids et la preuve associée** :

| Type d'arête | Nature | Affichage |
|--------------|--------|-----------|
| Transfert direct, TIP | Observée | Trait plein |
| Premier financeur commun (hors hub) | Inférée forte | Trait épais en pointillés |
| Destination de retrait commune | Inférée | Pointillés |
| Trades synchronisés (même issue, Δt ≤ 10 min) | Inférée faible | Pointillés fins |

- **Hubs** : un financeur qui alimente au moins 50 adresses, ou une adresse connue d'exchange ou de bridge, est marqué comme hub et **ne crée pas de lien**.
- **Communautés** : détection par l'algorithme de **Leiden** sur le graphe pondéré, puis score agrégé par cluster (PnL total, p-value combinée, synchronisation).

### 5.4 Score et calibration

- **Phase 0 / V1** : un score simple et lisible (régression logistique fortement régularisée), entraîné sur des **étiquettes faibles** :
  - **positifs** : les cas poursuivis ou documentés publiquement, environ quelques dizaines de wallets ;
  - **négatifs** : un échantillon aléatoire de wallets actifs.

  On affiche la contribution de chaque signal au score.
- **Validation** : protocole fixé **avant** de regarder les résultats.
  - rappel sur les cas connus en validation croisée par cas (*leave-one-case-out*) ;
  - taux de faux positifs sur un échantillon relu à la main ;
  - précision sur les k comptes les mieux classés (précision@k) ;
  - **délai de détection par rapport à l'annonce**.
- **Plus tard** : gradient boosting ou modèles de graphe seulement si les données étiquetées le justifient, avec validation chronologique (*walk-forward*).

### 5.5 Garde-fous (AI Act, RGPD)

- Le score décrit un **comportement de trading** (« flux informé »), pas une personne.
- Aucune donnée d'identité.
- C'est toujours toi qui décides.

---

## 6. Aide à la décision

### 6.1 Fiche de décision (une par signal)

| Élément | Contenu |
|---------|---------|
| Marché et issue | Ce que l'initié présumé a acheté |
| Prix | Son prix d'entrée et le prix actuel |
| Preuves | Liste des signaux déclenchés, avec liens vers les faits |
| Estimation | Probabilité de l'issue estimée à partir des backtests (Phase 0) |
| **Avantage restant** | Estimation − prix actuel − frais − slippage pour la taille envisagée |
| Contexte | Délai avant la résolution ; règles de résolution et risque de litige |
| Taille suggérée | Fraction de Kelly prudente (¼ ou moins), plafonnée |
| Actions | Bouton « paper trade » et journal de la décision |

### 6.2 Comptes « fiables »

Un compte est jugé fiable sur des critères mesurés, pas sur son PnL affiché :
- markouts positifs et persistants ;
- compétence significative après correction du multi-test ;
- stabilité dans le temps, mesurée hors échantillon.

L'étude montre que le PnL brut est un mauvais filtre : il ne recoupe les comptes compétents qu'à 12 %.

Ils sont évalués **par catégorie**, car un bon trader politique peut perdre en sport, et **nets des frais et du délai de copie**. Les clusters permettent de suivre leurs wallets secondaires.

### 6.3 Autres stratégies de positions

L'étude classe ces pistes, au-delà du suivi d'initiés, par intérêt pour un outil perso. Toutes passent d'abord par le paper trading.

| # | Piste | Intérêt | Difficulté | Ce que l'outil doit croiser | Version |
|---|-------|---------|------------|-----------------------------|---------|
| P1 | **Évaluer les wallets en walk-forward**, par catégorie, nets de frais et de délai | Fort | Moyenne | Trades, résolutions, frais | V1 |
| P2 | **Alerte « wallet neuf ciblé » et graphe de financement**, comme contexte d'un marché plutôt que comme ordre de copie | Fort | Moyenne | Transferts Polygon, horaires des annonces | V1/V2 |
| P3 | **Score de risque de résolution** pour les quasi-certitudes à 95-99 ¢. Une perte efface environ 19 gains. Taux de litige : 4,8 % en géopolitique. Exemple : 10,5 M$ non payés sur l'« invasion » du Venezuela. | Fort | Moyenne | Texte des règles, historique des litiges UMA, catégorie | V2 |
| P4 | **Météo** : prévisions d'ensemble (GFS, ECMWF via Open-Meteo, gratuites) comparées aux prix des tranches, surtout 1 à 12 h avant la clôture | Fort à moyen | Moyenne | Open-Meteo, station de résolution, carnet | V3 |
| P5 | **Calibration par catégorie et par horizon** (biais favori/outsider plus marqué sur les marchés en échelle de seuils) | Moyen | Faible | Historique des prix et des résolutions | V1 (sert aussi à S3) |
| P6 | **Cotes sportives (Pinnacle) et Kalshi** comme « juste prix », avec des ordres limites | Moyen | Moyenne | API de cotes, API Kalshi | V3 |
| P7 | **Market making récompensé** sur des marchés calmes | Moyen | Élevée | Récompenses, volatilité, actualité | Plus tard |
| P8 | **Arbitrage** (neg-risk, entre plateformes) | Faible | Élevée | Carnets temps réel | Écarté : réservé aux bots rapides, tailles minuscules |

Le **paper trading simule le mode d'exécution**. Un ordre limite (maker) est gratuit et reçoit une remise, mais il peut ne pas être exécuté. Un ordre au marché (taker) est exécuté immédiatement, mais il paie des frais et du slippage.

---

## 7. Interface V1 (volontairement basique)

| Écran | Contenu |
|-------|---------|
| **Radar** | Flux en direct des trades signalés, avec filtres (catégorie, taille, score). |
| **Marché** | Courbe de prix avec les trades des comptes signalés et les événements d'actualité placés dessus ; principaux détenteurs. |
| **Compte** | Profil, PnL, positions, signaux avec leurs preuves, cluster d'appartenance. |
| **Graphe** | Bulles et liens façon Bubblemaps, avec filtres par marché, par période et par type de lien ; clic sur une bulle pour ouvrir le compte. |
| **Paper trading** | Positions simulées, journal, performance. |

---

## 8. Architecture technique

```
 Data API v2 / Gamma ──┐   GitHub Actions (Python, toutes les 15-30 min)
 CLOB (prix, carnets) ─┼─> collecte + analyse (signaux, graphe, scores) ─> Neon PostgreSQL
 RPC / Etherscan ──────┤                                                        │
 Actualités, Kalshi ───┘                                                        v
                                                 Vercel : API + interface web (accès privé)
```

Plus tard, si la Phase 0 montre qu'il faut du temps réel, un collecteur permanent (flux RTDS, machine allumée 24 h/24) pourra alimenter la même base.

| Couche | Choix | Pourquoi |
|--------|-------|----------|
| Collecte | Python 3.12+, asyncio, `httpx`, `websockets`, Pydantic v2 | Validation stricte des réponses : les API ont beaucoup changé en 2026 et il faut détecter les ruptures. |
| Stockage | **PostgreSQL** : Neon en production, local en développement | PostgreSQL est imposé par l'organisation. Comme Neon gratuit est limité à 1 Go, on ne stocke que les marchés et les wallets utiles (F-06), et on recalcule les historiques à la demande depuis l'API. |
| Schéma | SQLAlchemy 2 (Core) + Alembic (migrations) | Schéma versionné, migrations reproductibles. |
| Analyse | Polars ou pandas, SciPy, statsmodels, igraph + leidenalg, scikit-learn | Bibliothèques standard et testées. |
| API et interface | **Next.js** (React, TypeScript) sur Vercel ; **Sigma.js** (WebGL) pour le graphe ; **lightweight-charts** pour les courbes | Next.js est l'outil naturel de Vercel. L'interface lit les résultats que les tâches Python ont déjà calculés. Sigma.js affiche des milliers de bulles de façon fluide. |
| Phase 0 | Bibliothèque Python + scripts qui produisent un rapport | Les tâches de collecte et d'analyse de la V1 réutilisent ce code. |
| Déploiement | Vercel (interface et API), Neon (base), GitHub Actions (collecte planifiée en Python) | Tout est gratuit et il n'y a aucun serveur à maintenir (§ 10). |

---

## 9. Qualité technique

| Domaine | Exigences |
|---------|-----------|
| Code Python | `uv`, `ruff` (lint et formatage), `mypy --strict`, docstrings sur les fonctions de calcul. |
| Tests | `pytest` avec une vraie base PostgreSQL de test (pas de simulation de la base). Tests de propriétés (`hypothesis`) sur le PnL : par exemple, la somme des gains doit égaler les flux de trésorerie. Tests de contrat sur des réponses d'API enregistrées et anonymisées. |
| Code front | TypeScript strict, ESLint, Vitest, un test Playwright de bout en bout. |
| Intégration continue | GitHub Actions : lint, typage, tests à chaque push. |
| Qualité des données | Ingestion idempotente ; rapprochement de notre PnL avec celui de l'API (écart inférieur à 1 %) ; suivi du retard des collecteurs ; alerte si le schéma d'une API change. |
| Reproductibilité | Chaque score stocke la version de l'algorithme et ses paramètres. Les backtests sont rejouables. |
| Sécurité | Aucun secret dans le code ni dans Git (`.env` local, `.env.example` versionné). Aucune donnée réelle dans le dépôt, qui est public. Dépendances figées (fichier de verrouillage) et vérifiées ; aucun bot ni code tiers de trading (des dépôts piégés volent les clés). Si l'exécution d'ordres est un jour envisagée : wallet dédié, faible solde, clé dans le trousseau du système. |

---

## 10. Hébergement et coûts

**Décision : solution gratuite et sans serveur à gérer.** Vérifiée le 6/11/2026.

| Rôle | Service | Limites de l'offre gratuite |
|------|---------|-----------------------------|
| Phase 0 | Cet environnement Claude Code | Rien à déployer. |
| Interface web et API | **Vercel Hobby**, région Francfort (`fra1`) | Fonctions de 300 s maximum. Les tâches planifiées ne tournent qu'une fois par jour : la collecte se fait donc ailleurs. Protection « All Deployments + Vercel Authentication » gratuite, qui réserve l'accès à ton compte. |
| Base de données | **Neon Postgres**, région Francfort | 1 Go par projet. 100 heures de calcul par mois, et la base s'endort après 5 min d'inactivité. On regroupe donc les écritures en lots pour ne pas la réveiller en permanence. |
| Collecte planifiée | **GitHub Actions** (dépôt public) | Une exécution toutes les 15-30 min au mieux, souvent retardée. Les tâches sont désactivées après 60 jours sans activité sur le dépôt. Les journaux d'exécution sont publics : on n'y affiche jamais de données. |

**Ce montage a deux limites :**
- **pas de temps réel à la seconde** : il faudrait une machine allumée en permanence (un PC ou une VM gratuite d'Oracle Cloud). La Phase 0 dira si l'avantage disparaît trop vite pour s'en passer ;
- **pas d'enregistrement fin des carnets d'ordres.** Le paper trading estime donc le slippage à partir des trades.

L'outil n'est pas accessible publiquement. Afficher les cotes de Polymarket à tout le monde pourrait constituer une promotion illégale en France.

Toutes les données sont stockées dans l'UE.

| Poste | Proposition |
|-------|-------------|
| Données | **0 €/mois** suffit pour la Phase 0 et la V1 : API Polymarket, Etherscan v2, RSS, Telegram, GDELT, adsb.lol, Kalshi. Environ 50 €/mois ajoute l'API X et Bitquery (origine des fonds). Environ 300 €/mois ajoute Dune et Nansen. Détail dans [`etude/C_sources_donnees.md`](etude/C_sources_donnees.md). |

À vérifier : le blocage de Polymarket par les FAI français concerne `polymarket.com`. Il faut tester depuis ta connexion que les API de données restent accessibles. Si elles ne le sont pas, on en discute ; on ne contourne pas le blocage.

---

## 11. Risques

| Risque | Probabilité | Impact | Réponse |
|--------|-------------|--------|---------|
| Le flux RTDS (non documenté) disparaît | Moyenne | Fort | Repli par interrogation de `/v2/trades` (F-01), surveillance du flux. |
| L'avantage restant est nul après détection | **Élevée** | Fort | Phase 0 avant d'investir dans la partie positions ; autres stratégies (§ 6.3). |
| Faux positifs (compétence ou chance prises pour une info privilégiée) | Élevée | Moyen | Tests statistiques avec contrôle du FDR, calibration, relecture humaine. |
| Polymarket bannit ou durcit l'accès, ou change ses API | Moyenne | Moyen | Couche d'accès isolée et testée. |
| Cadre légal défavorable au trading réel | Certain (France) | Fort | Paper trading ; avis d'un avocat avant tout passage au réel. |
| Volume de données important (Neon gratuit limité à 1 Go) | Moyenne | Moyen | Filtres (F-06), purge des données anciennes, recalcul à la demande depuis l'API. |

---

## 12. Décisions

**Prises le 6/11/2026 :**
- **Hébergement** : solution gratuite, sans serveur à gérer (§ 10).
- **Budget données** : 0 €/mois au départ. Une source payante ne sera ajoutée que si la Phase 0 en montre l'utilité.
- **Code** : choix techniques laissés à Claude, avec l'exigence de qualité du § 9.
- **Ordre** : la Phase 0 en premier.
- **Dépôt** : public, sans aucune donnée réelle.

**Encore ouvert :**
- **Lieu de résidence** (France ?). Il détermine si la partie « positions » reste en paper trading ou peut passer en réel.
