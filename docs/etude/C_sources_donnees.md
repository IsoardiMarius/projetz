# Sources de données pour l'outil d'analyse Polymarket (6 novembre 2026)

Prix relevés en ligne le 6/11/2026, sur les pages officielles quand elles existent. « ≈ » signale une source tierce ou une estimation. Aucun compte n'a été créé.

## À savoir d'abord

1. **Cadre légal, bloquant pour « prendre des positions »** : l'ANJ fait bloquer Polymarket par les FAI français depuis le 16/07/2026. Diffuser publiquement ses cotes peut constituer un délit de promotion. Kalshi est réservé aux résidents américains et Betfair est indisponible en France. Je recommande un outil d'observation strictement privé.
2. **RGPD** : une adresse rattachée à une personne (labels Arkham ou Nansen) est une donnée personnelle, et la qualifier d'« initiée » touche aux infractions présumées. Restez au niveau pseudonyme : pas de dé-anonymisation de particuliers, aucune publication, une durée de conservation fixée.
3. **Contrats v2** : Polymarket a migré le 28/04/2026, et les subgraphs publics sont devenus incomplets depuis. Vérifiez que chaque fournisseur couvre la v2.
4. **Stockage** : PostgreSQL (règle de l'organisation), éventuellement avec TimescaleDB.

**Dater une information (usage a)** : conservez l'horodatage de la source **et** votre propre heure de première détection (horloge synchronisée par NTP), puis comparez-les au `block_timestamp` Polygon du trade (≈2 s). Par fiabilité décroissante : X et Telegram (à la seconde), RSS officiels (à la minute, heure du CMS parfois décalée : l'Élysée a publié le 3/11 un entretien tenu le 2/11), GDELT (lots de 15 min), Google News.

## 1. Blockchain et analytics

| Source | Ce qu'elle ajoute aux API Polymarket | Coût/mois | Limites / licence | Intégration | Priorité |
|---|---|---|---|---|---|
| [Etherscan API v2](https://docs.etherscan.io/etherscan-v2/rate-limits) (Polygonscan) | Transferts ERC-20 **par adresse** (premier dépôt USDC, plateforme d'échange d'origine), ce que le RPC ne fournit pas | Gratuit (≈3 à 5 appels/s, 100 000/jour ; Polygon pas encore passé en payant). Labels [`getaddresstag`](https://docs.etherscan.io/api-reference/endpoint/getaddresstag) : plan Pro Plus (≈899 $) | Quotas partagés | Facile | Indispensable |
| [Dune](https://docs.dune.com/data-catalog/curated/prediction-markets/polymarket/overview) | Historique SQL `polymarket_polygon.*` : trades, positions, `users_address_lookup` (proxy → propriétaire, premier financement). Labels plateformes d'échange et bridges (`cex.addresses`, `labels.addresses`). Mise à jour ≈1 h | [Analyst 75 $](https://docs.dune.com/resources/credits-billing/how-credits-work) (65 $ en annuel), 4 000 crédits. Plan gratuit limité à la consultation, sans API | Crédits vite épuisés | Facile | Utile (fort) |
| [Goldsky Turbo Pipelines](https://docs.goldsky.com/chains/polymarket) | Flux temps réel v2 (`order_filled`, `user_positions` avec PnL) vers PostgreSQL | Crédit unique de 100 $, puis 1 worker et 1 million d'écritures/mois gratuits ([tarifs](https://docs.goldsky.com/pricing/summary)) | Rattrapage historique énorme : filtrer | Moyenne | Utile |
| [Bitquery](https://bitquery.io/pricing) | GraphQL et flux temps réel, [requêtes « initié » prêtes à l'emploi](https://docs.bitquery.io/docs/examples/polymarket-api/polymarket-insider-detection-api/) : wallet neuf, origine des fonds, wallets liés | Personal 29 $ (annuel, sans flux temps réel). Pro 69 $ (avec flux). Historique Polymarket : +105 $ | Personal non commercial ; prix incohérents sur la page | Facile | Utile |
| [Nansen](https://docs.nansen.ai/getting-started/credits) | [API Prediction Market](https://docs.nansen.ai/api/prediction-market.md) (PnL, taux de réussite, âge du wallet), labels « Smart Money » et plateformes d'échange | Pro 49 $ (annuel) ou 69 $, 2 000 crédits. Un label coûte 100 à 500 crédits | À réserver aux suspects | Facile | Utile |
| [Arkham](https://intel.arkm.com) | Entités nommées, graphe des flux | Interface gratuite. API sur candidature, tarif non publié | Recherche manuelle ; RGPD | Facile en manuel | Utile |
| [Allium](https://docs.allium.so/historical-data/supported-blockchains/evm/polygon/predictions.md) | SQL `polygon.predictions.trades` | 20 000 crédits offerts, puis sur devis (≈200 $ et plus) | Tarifs non publiés | Moyenne | Plus tard |
| [The Graph](https://thegraph.com/pricing.md) | Subgraphs | 100 000 requêtes/mois gratuites, puis ≈2 $ les 100 000 | Subgraphs Polymarket obsolètes (v2) | Facile | Plus tard |
| [Flipside](https://docs.flipsidecrypto.xyz/support/product-special-releases/2025/2025-06-20-or-deprecating-studio-dashboards-api-sdk) | Rien | Studio et API fermés en 2025 | — | — | À écarter |
| Chainalysis / TRM | Attribution d'adresses de référence ([outil de Polymarket depuis avril 2026](https://bloomberg.com/news/articles/2026-04-30/polymarket-adds-new-detection-tools-after-insider-bet-backlash)) | Devis entreprise (≈10 000 $ et plus par an). Seuls les outils de contrôle des sanctions sont gratuits | Hors budget, c'est confirmé | — | À écarter |

## 2. Actualités et événements horodatés

| Source | Apport | Coût/mois | Latence / limites | Intégration | Priorité |
|---|---|---|---|---|---|
| [X API](https://docs.x.com/x-api/getting-started/pricing) | Source la plus rapide (comptes officiels, journalistes, OSINT) | Paiement à l'usage : 0,005 $ par post lu (10 000 posts = 50 $), plafond de 3 millions/mois. Plus d'offre gratuite ni Basic | Secondes. Flux filtré en paiement à l'usage non confirmé | Moyenne | Indispensable |
| [Telegram](https://core.telegram.org/api) (Telethon) | Canaux OSINT et de suivi des conflits, souvent en avance sur la presse | Gratuit | Quelques secondes. Compte avec numéro de téléphone, limites anti-flood, [conditions d'utilisation](https://core.telegram.org/api/terms) | Moyenne | Indispensable |
| RSS officiels : [Maison-Blanche](https://www.whitehouse.gov/presidential-actions/feed/), [war.gov](https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=10), [Élysée](https://www.elysee.fr/feed) (tous testés) | Source primaire, souvent celle qui sert à résoudre le marché | Gratuit | Interroger toutes les 1 à 2 min | Facile | Indispensable |
| [GDELT 2.0](https://www.gdeltproject.org/about.html) | Presse mondiale multilingue ; date rétroactivement la première mention | Gratuit, tout usage avec citation | Lots de 15 min ; erreurs 429 fréquentes | Moyenne | Indispensable |
| [Google News RSS](https://news.google.com/rss/search?q=Iran) | Veille par mots-clés | Gratuit | Non officiel, quelques minutes de retard (≈) | Facile | Utile |
| [Wayback Machine CDX](https://archive.org/developers/wayback-cdx-server.html) | Prouver après coup à quelle heure une page existait | Gratuit | Captures irrégulières | Facile | Utile |
| [Event Registry](https://newsapi.ai/plans) | Articles et événements dédupliqués, archives depuis 2014 | Gratuit (2 000 recherches) ; 90 $ | Latence non publiée | Facile | Plus tard |
| [NewsAPI.org](https://newsapi.org/pricing) | Titres | Plan gratuit avec 24 h de retard, interdit en production ; 449 $ | Inadapté | — | À écarter |
| AP / Reuters | Dépêches de référence | Devis entreprise (plusieurs milliers $, non publié) | Licence réservée aux médias | Difficile | Hors budget |
| Agrégateurs de flashs (FinancialJuice, Tree News) | Titres en quelques secondes | Tarifs introuvables ; suivre leurs comptes via l'API X | Aspiration et redistribution interdites | — | Utile (via X) |

## 3. Données alternatives

| Source | Apport | Coût/mois | Limites | Intégration | Priorité |
|---|---|---|---|---|---|
| [adsb.lol](https://api.adsb.lol/docs) | `/v2/mil` (avions militaires), sans clé (testé), licence ODbL | Gratuit | Sans garantie de service | Facile | Indispensable (marchés géopolitiques) |
| [ADS-B Exchange](https://www.adsbexchange.com/api-lite/) | Réseau dense, données non filtrées | 10 $ (10 000 requêtes) | Usage personnel uniquement | Facile | Utile |
| [OpenSky](https://openskynetwork.github.io/opensky-api/rest.html) | Historique des vols | Gratuit (4 000 crédits/jour, OAuth2) | Non commercial | Facile | Plus tard |
| [FAA NOTAM](https://www.faa.gov/about/initiatives/notam/faqs) | Fermetures temporaires d'espace aérien, déplacements de personnalités | Gratuit, accès sur demande | Migration NMS en cours ; hors États-Unis, sources disparates | Moyenne | Utile |
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/) | Anomalies thermiques (frappes, incendies) | Gratuit (clé MAP_KEY) | ≈3 h de latence | Facile | Utile |
| [aisstream.io](https://aisstream.io) | Suivi AIS des navires (pétroliers, Ormuz, mer Rouge) | Gratuit. MarineTraffic : sur devis | Navires militaires souvent silencieux | Moyenne | Plus tard |
| [Copernicus](https://dataspace.copernicus.eu) / [SkyFi](https://skyfi.com/files/SkyFi_Pricing_2025.pdf) | Imagerie gratuite à 10 m / très haute résolution à la commande | Copernicus gratuit. SkyFi : archives 5 à 22,5 $/km² (minimum 5 km²), prise de vue dès 200 $. Planet/Vantor : sur devis | Plusieurs jours entre deux passages : sert à vérifier, pas à alerter | Moyenne | Plus tard |
| « Pentagon pizza index » ([pizzint.watch](https://pizzint.watch)) | Affluence Google Maps autour du Pentagone | Gratuit, sans API | Très bruité ; aspirer Google Maps viole ses conditions | Difficile | Anecdotique |

## 4. Autres marchés

| Source | Apport | Coût/mois | Limites | Intégration | Priorité |
|---|---|---|---|---|---|
| [Kalshi](https://docs.kalshi.com/getting_started/historical_data) | Un écart de cote avec ce marché régulé est un signal | Gratuit, lecture sans authentification (testé) | Trading réservé aux résidents américains | Facile | Indispensable |
| [Manifold](https://github.com/manifoldmarkets/manifold/blob/main/docs/docs/api.md) / [Metaculus](https://raw.githubusercontent.com/Metaculus/metaculus/main/docs/openapi.yml) | Prévisions de référence, signal faible | Gratuit (jeton sur demande pour Metaculus) | Licence commerciale sur demande | Facile | Plus tard |
| [The Odds API](https://the-odds-api.com/) | Cotes des bookmakers (en politique : seulement la présidentielle américaine) | Gratuit, puis 30 $ ou 59 $ | Couverture politique faible | Facile | Plus tard |
| [Betfair Exchange](https://betfair-datascientists.github.io/api/apiappkey/) | Bourse de paris avec des marchés politiques | Clé temps réel : 299 £ (paiement unique) | Indisponible en France | Moyenne | À écarter |
| [Massive](https://massive.com/futures) (ex-Polygon.io) | Contrats à terme CME : pétrole, or | Gratuit (5 requêtes/min) ; 29 $ (10 min de différé) ; temps réel : 999 $ | Pas de VIX | Facile | Utile |
| [Databento](https://databento.com/pricing) | Transactions CME horodatées finement | 125 $ de crédits offerts ; 199 $ en temps réel | — | Moyenne | Plus tard |
| [FRED](https://fred.stlouisfed.org/series/VIXCLS) / [Twelve Data](https://twelvedata.com/pricing) | VIX, pétrole, or | Gratuit | Granularité, délais | Facile | Utile |

## Trois piles de données selon le budget

**0 €/mois** : API Polymarket et RPC (déjà acquis), Etherscan v2, crédit Goldsky. Actualités : RSS officiels, Telegram, GDELT, Google News, Wayback. Données alternatives : adsb.lol, OpenSky, FIRMS, NOTAM, aisstream. Marchés : Kalshi, FRED, Massive gratuit. PostgreSQL en local. Il manque X et les labels automatiques.

**≈50 €/mois (≈59 $)** : le palier 0 €, plus l'API X (≈20 $, soit ≈4 000 posts de comptes primaires), ADS-B Exchange (10 $) et Bitquery Personal (29 $ : origine des fonds, wallets liés). Variante : un mois de Dune Analyst, activé seulement en cas de besoin.

**≈300 €/mois (≈350 $)** : le palier 50 €, avec X porté à ≈100 $, plus Dune Analyst (75 $), Nansen Pro (69 $) et Massive Starter (29 $). Bitquery Pro (69 $, flux temps réel) remplace le plan Personal, ou Goldsky Scale à sa place.

**Hors budget dans tous les cas** : Chainalysis, TRM, AP/Reuters, labels Etherscan, Planet/Vantor, X Enterprise.
