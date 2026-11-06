# Phase 0 — Méthode

La Phase 0 doit répondre à une question avant de construire la partie « positions » : **un détecteur simple aurait-il repéré à temps les comptes informés, et restait-il de l'argent à gagner en les suivant ?**

Le rapport chiffré est généré en local avec `uv run radar phase0-report`. Il n'est pas versionné, car il contient des données réelles.

## Données

- **Cas connus** (`src/radar/phase0/cases.py`) : six affaires où une information privilégiée a été alléguée ou établie (Nobel 2025, Google 2025, Maduro, frappes sur l'Iran, Khamenei, cessez-le-feu d'avril 2026). On n'y liste que des **marchés**, jamais de wallets : l'analyse doit retrouver seule les comptes concernés.
- **Échantillon large** (`src/radar/phase0/sample.py`) : tirage aléatoire reproductible de marchés géopolitiques résolus entre octobre 2025 et octobre 2026, avec un volume compris entre 50 k$ et 30 M$. Il évite de juger le détecteur sur les seuls cas où il a « marché ».
- **Trades** : pour chaque marché, toutes les exécutions des deux côtés (taker et makers), via la Data API v2. Le rapprochement entre le flux taker et le flux complet sert de contrôle de cohérence : 0 ligne non rapprochée sur les cas collectés.
- **Wallets** : première activité (dépôts compris) et dépôts. Les dépôts groupés vers 5 wallets ou plus sont exclus, car ce sont des distributions de récompenses.

## Détecteur (règles fixées avant de voir les résultats)

- **Signal** : un wallet a acheté au moins **1 000 $** d'une issue à **35 ¢ ou moins**. Le signal est daté du trade qui franchit ce seuil.
- **Alerte** : un signal émis par un wallet de **7 jours au plus** au moment du signal.

Seules des informations disponibles à l'instant du signal sont utilisées. L'analyse de sensibilité présente **tous** les réglages testés (prix max 0,20 / 0,35 / 0,50 ; mise min 500 / 1 000 / 5 000 $ ; âge max 2 / 7 / 30 jours), sans en retenir un a posteriori.

## Suiveur simulé

- Il achète la même issue **au marché** : le prix de la première exécution côté vendeur après son retard, et jamais dans le bloc du signal.
- Retards testés : bloc suivant, 1 min, 5 min, 15 min, 30 min, 1 h, 4 h. Ils correspondent à un suivi temps réel, à un suivi minute par minute et à une collecte toutes les 15-30 min (GitHub Actions).
- Frais taker selon le barème actuel ; la position est gardée jusqu'à la résolution.
- Petite mise (100 $) : l'impact de son propre ordre est négligé, faute d'historique du carnet d'ordres.

## Mesures

| Mesure | Ce qu'elle dit |
|--------|----------------|
| Part d'issues gagnantes, comparée au prix payé | Si elle dépasse la probabilité implicite du prix, ces acheteurs savaient mieux que le marché. |
| Rendement du suiveur selon le retard | Ce qu'il reste à gagner, et à quelle vitesse cela disparaît. Cette courbe décide s'il faut du temps réel, donc un serveur. |
| Avance des alertes sur l'information | Combien de temps avant que l'issue devienne évidente l'alerte se déclenche. Ce moment est estimé a posteriori sur les prix : premier passage au-dessus de 85 % après le dernier passage sous 50 %. |
| Plus gros acheteurs gagnants avant l'information | Vérification rétrospective : le détecteur les aurait-il repérés ? |

**Incertitude** : intervalles de confiance à 90 % par bootstrap d'**événements**. Les marchés d'un même événement sont corrélés, et les compter comme indépendants exagérerait la précision.

## Limites connues

- La première activité d'un wallet est lue sur ses 300 premières lignes d'activité : c'est fiable pour l'âge, mais incomplet pour les dépôts tardifs des gros comptes.
- Le barème de frais actuel est appliqué aux trades anciens, ce qui est prudent : les frais étaient plus bas avant 2026.
- Il n'y a pas d'historique du carnet d'ordres : le slippage des grosses mises n'est pas mesuré.
- Les initiés expérimentés utilisent des comptes anciens ou camouflés. La règle « wallet récent » ne vise que les plus visibles ; les clusters de wallets (V1) iront plus loin.
