# Phase 0 — Résultats (6 novembre 2026)

> Synthèse **agrégée** : aucun wallet ni aucune donnée individuelle. Le rapport détaillé (tableaux par compte, graphiques) est généré en local par `uv run radar phase0-report` et n'est pas versionné. Méthode : [`phase0_methode.md`](phase0_methode.md).

## Données

- **409 marchés résolus**, soit **4,1 millions** d'exécutions, toutes cohérentes (0 ligne non rapprochée) :
  - **9 marchés** pour 6 cas connus : Nobel 2025, Google 2025, Maduro, frappes sur l'Iran, Khamenei, cessez-le-feu d'avril 2026 ;
  - **400 marchés géopolitiques** tirés au hasard (250 événements, octobre 2025 à octobre 2026).
- **Âge connu pour 100 % des wallets** ayant émis un signal (6 143 wallets profilés).

## Règle testée

- **Alerte** : un wallet de **7 jours au plus** qui a acheté pour **≥ 1 000 $** d'une issue cotée **≤ 35 ¢**. Cette règle a été fixée avant de voir les résultats.
- **Suiveur simulé** : il copie l'alerte au marché, de « dès le bloc suivant » jusqu'à 4 h de retard, frais compris, et garde la position jusqu'à la résolution.

## Résultats

### 1. Sur les cas connus, le détecteur voit bien les comptes suspects…

- Sur 8 des 9 marchés, les alertes émises avant l'annonce portaient presque toutes sur la bonne issue. Exemple : 195 sur 204 pour « frappes avant le 28 février ».
- Leur avance va de quelques heures à plusieurs jours.
- Le Nobel est l'exception : 1 alerte sur 9 seulement avait vu juste. La fuite a eu lieu la nuit précédant l'annonce, et la plupart des comptes neufs ont parié sur d'autres candidats.
- Mais parmi les 5 plus gros gagnants de chaque marché, **seuls 11 sur 45 (un quart environ)** étaient des comptes récents. Les autres sont des comptes anciens, souvent positionnés des jours ou des semaines avant. C'est le profil d'une **conviction ou d'une compétence**, pas forcément d'un initié.

**Attention au biais de sélection.** Ces marchés ont été choisis *parce que* l'outsider a gagné : tout acheteur de la bonne issue y a gagné. Les +380 % de rendement moyen des suiveurs sur ces cas ne prouvent donc rien.

### 2. … mais, sur des marchés tirés au hasard, suivre ces alertes fait perdre de l'argent

| Population (marchés tirés au hasard) | Signaux | Issue gagnante | Prix moyen payé | Rendement du suiveur (bloc suivant) | Rendement (4 h) |
|---|---|---|---|---|---|
| Alertes : wallets ≤ 7 j | 241 (56 événements) | **9 %** [7 ; 13] | 17 % | **−45 %** [−75 ; −6] | −63 % [−83 ; −39] |
| Autres signaux : wallets anciens | 2 301 (148 événements) | 17 % [15 ; 18] | 20 % | −24 % [−52 ; +7] | +6 % [−56 ; +90] |

*Entre crochets : intervalles de confiance à 90 %, calculés par bootstrap d'événements.*

- **Les comptes récents qui achètent un outsider gagnent moins souvent que le prix ne l'annonce** : 9 % contre 17 % attendus. Ce sont surtout des parieurs, pas des initiés.
- **Aucun des 27 réglages testés n'est robustement positif.** Les seuils couvrent un prix de 20 à 50 ¢, une mise de 500 à 5 000 $ et un âge de 2 à 30 jours. Les rares points positifs ont des intervalles qui chevauchent zéro, ce qu'on attend du hasard sur 27 essais.
- **Les comptes anciens** suivent le léger biais favori/outsider du marché (17 % contre 20 %) : aucun avantage à les copier en bloc.

### 3. La vitesse n'est pas le facteur limitant

Sur les cas connus, le rendement du suiveur est quasiment le même dès le bloc suivant ou 4 h après (+388 % contre +383 %). Le prix ne s'envole qu'au moment de l'annonce. Sur l'échantillon, il n'y a pas d'avantage à perdre. **Le temps réel à la seconde n'est donc pas prioritaire** : une collecte chaque minute (cron Cloudflare) suffit pour ce type de signal.

## Conclusions

1. **Pas de copy-trading sur la règle « compte récent + outsider »**. Elle repère les initiés visibles, mais elle est noyée sous les parieurs ordinaires : sa précision est trop faible pour être rentable.
2. **Le vrai chantier est la précision du détecteur.** Pistes, par ordre de priorité :
   - **clusters** : plusieurs comptes neufs synchronisés sur la même issue, avec un financement commun (hors hubs) ;
   - **type de marché** : marchés « à secret » (opérations, nominations, prix) plutôt que marchés spéculatifs à dates en échelle ;
   - **historique du wallet** par catégorie, évalué en walk-forward ;
   - combinaison **apprise et validée** hors échantillon, au lieu de seuils fixes.
3. **La partie « positions » doit explorer d'autres pistes** (cahier des charges, § 6.3), en paper trading :
   - P1 : suivre des comptes **compétents par catégorie**, sélectionnés en walk-forward ;
   - P3 : **score de risque de résolution** sur les quasi-certitudes à 95-99 ¢.
4. **Architecture** : la collecte toutes les minutes sur Cloudflare suffit. Le collecteur temps réel (Durable Object) devient optionnel.

## Proposition pour la suite (V1)

- **Socle déployé** :
  - collecte automatique sur Cloudflare (cron chaque minute) vers Neon ;
  - interface basique : radar des alertes, fiche marché avec timeline, fiche compte, **graphe à bulles des liens de financement**.
- **Itération sur le détecteur**, en réutilisant le jeu de données de la Phase 0 :
  - ajout des clusters et du type de marché ;
  - même protocole d'évaluation sur marchés tirés au hasard.
- **Paper trading** des pistes P1 et P3.
