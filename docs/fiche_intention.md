# Fiche d'intention — Observatoire des marchés de prédiction (nom provisoire)

> **Statut : cadrage d'un projet personnel.** Il n'y a ni PO ni K-lab : le développement commence sans validation formelle. Cet écart est consigné dans [`exception.md`](exception.md) (EXC-001).
> Rédigée le 6 novembre 2026 à partir de l'archive « Polymarket — Conversation et captures ».
> Porteur du projet : _à compléter_

---

## 1. Contexte

Polymarket est une plateforme de marchés de prédiction : on y achète des parts « oui » ou « non » sur des événements futurs (élections, conflits, météo…). Les comptes sont des portefeuilles (*wallets*) sur la blockchain Polygon. Leurs transactions sont donc publiques, mais leurs propriétaires ne sont pas identifiés.

Une vidéo d'Underscore_ avec un spécialiste de la cartographie blockchain (Bubblemaps) montre comment des groupes de comptes liés par des transferts ont gagné de fortes sommes sur des paris géopolitiques, peu avant des annonces publiques. Deux comptes pseudonymes cités dans cette vidéo ont réalisé plusieurs centaines de milliers de dollars de gains en quelques semaines. Leurs identifiants ne sont pas reproduits ici.

## 2. Problème

Il n'existe pas d'outil simple et transparent pour :

- suivre dans le temps l'activité de comptes publics sur un marché de prédiction ;
- confronter chaque pari à ce qui était **publiquement connu** au moment où il a été passé ;
- visualiser les liens financiers entre comptes, en distinguant ce qui est **observé** de ce qui est **supposé**.

## 3. Objectif

Construire un **outil d'analyse exploratoire** (OSINT) qui aide un analyste humain à repérer des **signaux d'anomalie** dans l'activité de comptes Polymarket, et à les documenter de façon sourcée et vérifiable.

### Ce que l'outil n'est pas

- Il **ne désigne pas de coupable** : une anomalie statistique n'est pas une preuve de délit d'initié.
- Il **ne cherche pas à identifier les personnes** derrière les comptes. Aucun rapprochement avec une identité civile, un réseau social ou une donnée hors chaîne n'est fait.
- Il **ne prédit pas** le comportement futur d'une personne.
- Il **ne publie rien** : les résultats restent internes au projet.

## 4. Utilisateurs

- Le porteur du projet et son équipe, en tant qu'analystes.

L'outil ne vise pas d'utilisateurs externes. Il ne contient pas de système de comptes : c'est un outil local, et si un accès partagé devient nécessaire, il passera par le SSO de l'organisation.

## 5. Périmètre

### V1 (MVP)

| # | Fonction | Résultat attendu |
|---|----------|------------------|
| 1 | Collecte | Historique des transactions et des positions d'une liste de comptes saisie à la main, et métadonnées des marchés concernés. |
| 2 | Suivi | Interrogation régulière des API et enregistrement idempotent des nouvelles opérations (pas de doublon). |
| 3 | Reconstitution | Positions, prix d'entrée et de sortie, gains et pertes (PnL) réalisés, par marché. |
| 4 | Timeline | Pour un marché : courbe de prix, paris des comptes suivis et événements publics datés (saisis à la main avec leur source). |
| 5 | Graphe | Transferts USDC sur Polygon entre comptes suivis, dans le style des captures Bubblemaps. Lien **observé** (transfert direct, hash à l'appui) ≠ lien **inféré** (source de financement commune). |
| 6 | Signaux | Règles simples et explicables : pari pris peu avant une annonce, gain sur une issue cotée à faible probabilité, compte neuf avec une forte mise, concentration sur un seul thème. Chaque signal pointe vers les faits qui l'ont déclenché. |
| 7 | Dossier | Export d'une fiche de faits par compte (hashes, horodatages UTC, sources), sans conclusion. |

### Hors périmètre de la V1

- Surveillance automatique de l'ensemble de Polymarket.
- Apprentissage automatique, score agrégé de « probabilité de fraude ».
- Alertes via Telegram, Discord ou un autre service externe.
- Déploiement chez un hébergeur ; mise en ligne publique.

## 6. Données

### Sources (vérifiées le 6 novembre 2026)

| Source | Usage | Accès |
|--------|-------|-------|
| Polymarket **Gamma API** | Marchés, événements, règles de résolution | Public, sans clé |
| Polymarket **Data API v2** | Transactions et activité d'un compte (`/v2/trades`, `/v2/activity`) | Public, sans clé. La v1 est retirée. |
| Polymarket **CLOB API** | Historique des prix d'un marché | Public, sans clé |
| Blockchain **Polygon** (nœud RPC ou indexeur) | Transferts USDC entre adresses | **Clé d'accès requise** : les nœuds publics gratuits sans clé ont été fermés. Le fournisseur est à faire approuver. |
| Événements publics | Communiqués, dépêches, déclarations officielles, avec date, heure et URL | Saisie manuelle |

Conditions d'utilisation des API Polymarket : à relire avant la collecte réelle, en respectant les limites de débit.

### Données personnelles

Une adresse de portefeuille et un pseudonyme sont des **données pseudonymes**. Ce sont des **données personnelles** au sens du RGPD dès qu'elles se rapportent à une personne physique qu'on peut identifier. Le projet consiste justement à relier des comptes entre eux, ce qui augmente le risque de ré-identification.

De plus, une base qui signale des comptes comme suspects de délit d'initié peut être considérée comme un traitement de **données relatives à des infractions présumées** (article 10 du RGPD, article 46 de la loi Informatique et Libertés). Ce type de traitement est très encadré. → **Point à clarifier avant toute collecte de données réelles** (voir § 13).

## 7. Mesures RGPD prévues dès la conception

| Principe | Mesure |
|----------|--------|
| Minimisation | On ne garde que l'adresse, le pseudonyme public et les transactions. Les champs `bio`, `profile_image` et `pseudonym` (généré automatiquement) renvoyés par l'API sont supprimés à la collecte. Aucun enrichissement avec des sources d'identité. |
| Données fictives | Le développement et les tests utilisent un **jeu de données fictif**. La collecte réelle reste désactivée par défaut et doit être activée volontairement. |
| Durée de conservation | Proposition : durée du projet, avec un maximum de 12 mois. Une purge automatique des transactions et des dossiers est intégrée à l'outil. La durée est à confirmer. |
| Droits des personnes | Une liste d'exclusion par adresse : une adresse exclue est purgée et n'est plus jamais collectée. Le point de contact pour exercer ses droits est à désigner. |
| Information | Une page « À propos des données » dans l'interface et une section dans le README : finalité, sources, durée de conservation, droits, contact. |
| Localisation | Base PostgreSQL locale (Docker), sans transfert hors UE. Pas d'alertes vers des messageries hébergées hors UE. |
| Confidentialité | Aucune donnée réelle dans Git (le dépôt est public, voir EXC-002) ; résultats non publiés. |
| Base légale | À déterminer : intérêt légitime ? Exemption journalistique ou de recherche ? |

## 8. AI Act

- L'outil n'utilise **ni** reconnaissance d'émotions, **ni** biométrie, **ni** notation sociale, **ni** manipulation des comportements.
- **Point de vigilance (article 5, paragraphe 1, point d, de l'AI Act)** : il est interdit d'évaluer le risque qu'une personne commette une infraction **sur la seule base de son profilage** ou de ses traits de personnalité. Pour rester clairement hors de ce champ, la conception s'impose les règles suivantes :
  - l'outil fait une analyse **a posteriori** de transactions déjà passées, pas une prédiction sur des personnes ;
  - chaque signal repose sur des **faits objectifs et vérifiables** : l'horodatage d'un ordre, l'horodatage d'une annonce publique sourcée, un transfert identifié par son hash ;
  - la V1 n'utilise **pas d'apprentissage automatique**, seulement des règles statistiques lisibles ;
  - il n'y a **aucun score de culpabilité** et aucune décision automatique : l'outil assiste l'analyste humain, qui reste seul juge.
- Le projet ne relève pas des cas à haut risque listés par l'organisation (étudiants, candidats, salariés, biométrie).
- Toute évolution vers un modèle d'apprentissage automatique demandera une **nouvelle évaluation** avant d'être codée.

## 9. Architecture envisagée

```
Collecte (Python + HTTPX)  →  Normalisation UTC + dédoublonnage  →  PostgreSQL
        →  Analyse (Pandas / SciPy / NetworkX)  →  API  →  Interface web (timeline + graphe)
```

- **Base de données : PostgreSQL**, imposée par l'organisation.
- **Graphe** : Cytoscape.js ou Sigma.js ; **courbes** : Plotly.
- **Exécution** : Docker Compose, en local.
- **Secrets** (clé du fournisseur Polygon) : dans des variables d'environnement, jamais dans le code ni dans Git.

## 10. Risques et points à arbitrer

| Risque | Impact | Réponse proposée |
|--------|--------|------------------|
| Traitement de données relatives à des infractions présumées | Juridique (RGPD) | Données fictives par défaut ; collecte réelle seulement après une analyse juridique (voir § 13). |
| Diffamation, faux positif présenté comme une accusation | Juridique, réputation | Vocabulaire neutre (« signal », pas « suspect »), aucune publication, chaque fiche distingue faits, inférences et hypothèses. |
| **Le dépôt GitHub est public** (choix du builder, EXC-002) | Exposition du code et des données | Aucune donnée réelle versionnée ; jeux de test fictifs ; `.gitignore` strict. |
| Clé du fournisseur Polygon | Service externe à approuver, secret à protéger | Choix du fournisseur à valider ; clé gardée hors dépôt. |
| Évolution des API (la v1 a déjà été retirée) | Panne de la collecte | Couche d'accès isolée et tests sur des réponses enregistrées. |
| Données incomplètes (ordres hors chaîne, autres plateformes) | Conclusions faussées | Limites documentées dans chaque dossier. |

## 11. Critères de réussite de la V1

- Les gains et pertes reconstitués d'un compte (fictif, puis réel) correspondent à ceux affichés par Polymarket, à 1 % près.
- Une nouvelle transaction apparaît dans l'outil moins de 15 minutes après avoir été passée.
- Chaque signal affiché renvoie à au moins un fait vérifiable (hash, horodatage, URL de la source).
- Le graphe sépare visuellement les liens observés des liens inférés.

## 12. Planning indicatif

| Semaine | Livrable |
|---------|----------|
| 0 | Fiche de cadrage rédigée ; exceptions consignées. |
| 1 | Schéma PostgreSQL, collecteurs, jeu de données fictif, tests. |
| 2 | Reconstitution des positions et du PnL, suivi régulier. |
| 3 | Timeline marché / compte / événements. |
| 4 | Graphe des transferts et signaux explicables. |
| 5 | Export des dossiers, documentation, démonstration. |

## 13. Validations demandées

- [x] Validation K-lab ou PO : sans objet (projet personnel, EXC-001).
- [ ] Avant toute collecte de données réelles : vérifier la qualification juridique (article 10 du RGPD), la base légale, la durée de conservation et les mentions d'information. Les ressources de la CNIL ou l’avis d’un juriste peuvent aider.
- [ ] Choix du fournisseur d'accès Polygon et conservation de sa clé hors du dépôt.
