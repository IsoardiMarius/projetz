# A — Polymarket : ce qui est techniquement possible (6 novembre 2026)

**Légende** : **V** = vérifié, par un test en direct ou dans la documentation officielle ; **I** = incertain.
Les numéros entre crochets renvoient aux sources listées en fin de document.

## 1. Temps réel

- **Canal market du CLOB** : `wss://ws-subscriptions-clob.polymarket.com/ws/market`, public. **V** [1]
  - Il transmet le carnet complet (`book`), les variations de prix (`price_change`) et le dernier prix échangé (`last_trade_price`).
  - Le dernier prix échangé contient le hash de la transaction, **mais jamais l'adresse du wallet**.
  - On s'abonne actif par actif (`asset_id`).
  - Test sur 20 actifs : 4 818 messages en 25 s, avec environ 45 ms entre l'horodatage du serveur et la réception.
- **Canal user** : authentifié, il ne concerne que son propre compte. **V** [2]
- **RTDS, topic `activity`/`trades`** : `wss://ws-live-data.polymarket.com`, sans clé.
  - C'est un **flux global de tous les trades, avec l'adresse `proxyWallet`**, le pseudonyme, le marché, le prix, la taille et le hash de la transaction.
  - Test : 628 messages en 30 s, la nuit (heure des États-Unis), côtés maker et taker confondus.
  - Il recoupe environ 95 % des trades de `/v2/trades?taker_only=false` sur la même fenêtre.
  - L'horodatage correspond au moment du « match » des ordres. Il précède l'inscription dans le bloc Polygon de 1 à 2 s, et le message arrive en moins d'une seconde.
  - Ces mesures sont **V** (test), mais la **pérennité de ce flux est I** : la documentation se contredit. Une page dit « Keep using RTDS for the activity topic » [3], une autre « RTDS supports comments and crypto prices only » [4].
- **PolyBolt** : `wss://ws-live-v2.polymarket.com/ws`. Il ne transmet que des prix de référence (crypto, actions), demande une authentification CLOB et accepte au plus 64 abonnements. **V** [3]
- **Suivre un wallet précis** : aucun filtre par wallet n'est documenté. Il faut filtrer RTDS de notre côté, ou interroger régulièrement `/v2/activity?user=`. **I**
- **Latence de la Data API** : **V** (test)
  - `/v2/status` annonce un retard (`lag_seconds`) de 2 s.
  - Sans filtre, `/v2/trades` est à 0–1 s du temps réel.
  - Mais le CDN (CloudFront) met en cache les URL identiques pendant 5 min (`max-age=300`) : au test, la réponse est restée figée 56 s. Ajouter un paramètre qui change à chaque appel (`_=<ts>`) contourne ce cache.
- **Limites de débit** : appliquées par Cloudflare par adresse IP, en ralentissant les requêtes plutôt qu'en les rejetant. **V** [5]

  | API | Limite (requêtes par 10 s) |
  |-----|----------------------------|
  | Data API, toutes routes | 800 |
  | `/v2/trades` | 300 |
  | `/v2/activity`, `/v2/positions` | 200 |
  | Gamma, toutes routes | 4 000 |
  | Gamma `/markets` | 300 |
  | CLOB, toutes routes | 9 000 |
  | CLOB `/book` | 1 500 |
  | Bridge | 50 |

  - Ordres : 40 par seconde au palier Standard. **V** [6]
  - WebSockets : aucune limite documentée. **I**
- **User-Agent** : le User-Agent par défaut de Python est rejeté par Cloudflare (erreur 403, code 1010). **V** (test)

## 2. Historique complet d'un marché

- **`/v2/trades?condition=…`** : sans clé, pagination par curseur, 1 000 lignes par page.
  - Dans ce mode, `start` et `end` sont ignorés : la fenêtre est fixe (3 ans). Il faut parcourir tout le marché puis filtrer sur la période voulue. **V** [7]
  - Tests sur des marchés de février 2026 : **V** (test)
    - un marché : 9 593 trades en 10 pages et 3,5 s. La somme des tailles est égale au volume affiché par Gamma ;
    - un autre : 82 025 trades en 83 pages et 29 s, soit 99,999 % du volume.
  - Champs : `proxy_wallet`, side, size, price, timestamp, token_id, transaction_hash.
  - `taker_only=false` ajoute les lignes côté maker.
  - Le flux global, sans filtre de marché, ne couvre que le mois en cours et le précédent. **V** [7]
- **Subgraphs Goldsky** : abandonnés depuis le 28/04/2026. Les adresses publiques renvoient une erreur 404. Les remplaçants (Turbo Pipelines, Feeds API) demandent une clé ou un paiement. **V** [8]
- **Dune** : **V** [9]
  - `polymarket_polygon.market_trades` donne maker, taker, prix, montant, frais et `order_hash`, rafraîchi environ toutes les heures ;
  - `users_address_lookup` donne le lien entre proxy et propriétaire, ainsi que le premier financeur ;
  - accès gratuit et couverture des nouveaux Deposit Wallets : **I**.

## 3. Structure on-chain

- **Types de wallets** : **V** [10]
  - Deposit Wallet : type par défaut depuis le 4/05/2026 ;
  - Proxy : comptes Magic ou Google ;
  - Gnosis Safe : comptes MetaMask et autres.
- **Factories** (contrats qui créent les wallets) : **V** [11]
  - Deposit : `0x00000000000Fb5C9ADea0298D729A0CB3823Cc07`
  - Safe : `0xaacfeea03eb1561c4e67d661e40682bd20e3541b`
  - Proxy : `0xaB45c5A4B0c941a2F231C04C3f49182e1A254052`
- **Contrats d'échange** :
  - depuis le 28/04/2026 : CTF Exchange `0xE111180000d2663C0091e4f400237545B87B996B`, Neg Risk CTF Exchange `0xe2222d279d744050d28e00520010520000310F59`, CTF `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045`, Protocol V2 (PositionManager, ExchangeV3) **V** [11] ;
  - en février 2026 : ancien CTF Exchange `0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e`, avec l'USDC.e comme collatéral. **V** (test)
- **Collatéral** : pUSD (`0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB`, 6 décimales, adossé à l'USDC) remplace l'USDC.e depuis le 28/04/2026. La conversion passe par CollateralOnramp `0x93070a847efEf7F70739046A929D47a521F5B8ee`. **V** [12][4]
- **Arrivée des dépôts** : **V** [13]
  - par la Bridge API, avec une adresse de dépôt par chaîne (evm, svm, btc, tron) et conversion automatique en pUSD ;
  - par transfert direct d'USDC ou d'USDC.e ;
  - au-delà de 50 000 $, la documentation recommande deBridge, Across ou Portal.
- **Test sur un compte étudié** (5 dépôts de février 2026) :
  - Chaque dépôt est un `transferFrom` d'USDC.e depuis la même adresse « hub » (`0xf70d…`). **V** (test)
  - Ce hub a envoyé 3,3 millions de transactions et alimenté 24 destinataires en 50 blocs. Ses transactions sont émises par des relais tiers. **V** (test)
  - **On ne peut donc pas remonter plus loin que ce hub.** Son propriétaire (exchange ou bridge ?) : **I**.
- **Dépôts récents** (après le passage au pUSD) : l'USDC.e passe par une adresse déléguée EIP-7702, puis le pUSD est émis via un bundler ERC-4337. Cette adresse avait elle-même été alimentée par le hub 9 blocs plus tôt. **V** (test), interprétation **I**.
- **Piège** : certaines lignes `DEPOSIT` sont en réalité des distributions groupées de pUSD (environ 400 wallets en une transaction), probablement des récompenses. **Elles doivent être exclues** du graphe de financement.
- **Nœuds RPC publics** : **V** (test)
  - publicnode : pas d'accès aux données d'archive sans jeton ;
  - drpc : `eth_getLogs` limité à environ 50 blocs ;
  - 1rpc : `eth_getLogs` limité à 50 blocs.

## 4. Passer des ordres par API

- **SDK unifiés** : `polymarket-client` (Python) et `@polymarket/client` (TypeScript). L'ancien `py-clob-client` ne fonctionne plus depuis le 28/04/2026. **V** [14][15]
  - Authentification en deux niveaux : L1 (signature EIP-712), qui génère des identifiants L2 (HMAC).
  - Types d'ordres : GTC, GTD, FOK, FAK, post-only.
- **Frais** : **V** [16][4]
  - makers : 0 ;
  - takers : C × taux × p × (1 − p), où C est le nombre de parts et p le prix ;
  - taux : 0,07 (crypto), 0,05 (sports, économie, culture), 0,04 (politique, finance, tech), **0 (géopolitique)** ;
  - délai de 150 ms imposé aux takers sur les marchés crypto.
- **Géoblocage** : **la France est en « close-only » sur le site ET sur l'API**, ce qui permet de fermer des positions mais pas d'en ouvrir. Vérification : `GET https://polymarket.com/api/geoblock`. **V** [17]
- **Polymarket US** : plateforme distincte, régulée (via QCX), avec une API séparée accordée sur candidature. **V** [18]

## 5. Carnet d'ordres

- **En direct** : `GET /book`, `/books` (jusqu'à 500 tokens par requête) et le WebSocket market. **V**
- **Historique** : il n'existe **aucun endpoint officiel**, il faut l'enregistrer soi-même. Tardis le propose depuis le 25/05/2026 (payant, sauf le 1er jour de chaque mois). **V** [19]

## Contraintes structurantes pour l'architecture

1. Depuis la France, l'API d'ordres est en close-only : on ne copie pas de trades dans les règles, et on ne contourne pas le blocage.
2. Seul RTDS `activity` fournit le flux global avec les adresses des wallets, et il n'est pas documenté. Il faut un repli par interrogation de `/v2/trades`, avec une URL variable pour éviter le cache.
3. L'historique des trades est complet et gratuit via `/v2/trades?condition=`. En revanche, il n'existe ni subgraph ni historique du carnet : il faut l'enregistrer dès le départ.
4. Le graphe de financement s'arrête sur les hubs, les bridges et les adresses EIP-7702, et les RPC publics sont bridés. Il faudra un RPC avec clé, Etherscan v2 ou Dune.
5. Deux systèmes de positions coexistent, et le collatéral a changé (USDC.e puis pUSD) : le modèle de données doit absorber ces changements de contrats.

## Sources

1. https://docs.polymarket.com/api-reference/wss/market.md
2. https://docs.polymarket.com/trading/realtime-order-updates.md
3. https://docs.polymarket.com/migrate/rtds-to-polybolt.md
4. https://docs.polymarket.com/changelog/predictions.md
5. https://docs.polymarket.com/api-reference/rate-limits.md
6. https://docs.polymarket.com/api-reference/trading-rate-limits.md
7. https://docs.polymarket.com/api-reference/feeds/list-trades.md
8. https://docs.goldsky.com/chains/polymarket
9. https://docs.dune.com/data-catalog/curated/prediction-markets/polymarket/overview.md
10. https://docs.polymarket.com/trading/wallets-auth.md
11. https://docs.polymarket.com/resources/contracts.md
12. https://docs.polymarket.com/concepts/pusd.md
13. https://docs.polymarket.com/trading/bridge/deposit.md
14. https://docs.polymarket.com/migrate/clob-sdk-to-unified-sdk.md
15. https://docs.polymarket.com/trading/place-orders.md
16. https://docs.polymarket.com/trading/fees.md
17. https://docs.polymarket.com/api-reference/geoblock.md
18. https://polymarketexchange.com/developers.html
19. https://docs.tardis.dev/historical-data-details/polymarket
