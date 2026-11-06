# Exceptions au cadre de l'organisation

Ce fichier consigne chaque écart aux règles de l'organisation demandé pour ce projet : la règle concernée, le risque expliqué au builder, sa décision et les mesures prises pour limiter le risque.

---

## EXC-001 — Développement sans fiche d'intention validée

| Champ | Contenu |
|-------|---------|
| Date | 6 novembre 2026 |
| Règle concernée | Recommandation : « Pour une nouvelle application, évite de coder avant que sa fiche d'intention soit validée par le PO de l'équipe, ou par le K-lab pour un projet pédagogique. » |
| Nature | Recommandation (pas une interdiction) |
| Demande du builder | Commencer le développement tout de suite. Le builder précise qu'il s'agit d'un **projet personnel**, sans PO ni K-lab. |
| Risque expliqué | Sans validation, personne ne relit le projet avant le code. Les risques juridiques (données relatives à des infractions présumées, diffamation) ne sont pas arbitrés en amont, et une partie du travail pourrait être à refaire. |
| Décision | Le builder confirme : le développement commence. |
| Mesures compensatoires | Une fiche d'intention est tout de même rédigée (`docs/fiche_intention.md`) et sert de cadrage. Les obligations restent appliquées : RGPD dès la conception, aucune IA interdite par l'AI Act, PostgreSQL, aucun secret dans le code. Le développement utilise des **données fictives** par défaut. |
| Remarque | Les règles de l'organisation s'appliquent à toutes les sessions menées avec ce compte, y compris pour un projet personnel. C'est pourquoi cet écart est consigné. |

---

## EXC-002 — Dépôt GitHub public

| Champ | Contenu |
|-------|---------|
| Date | 6 novembre 2026 |
| Règle concernée | Recommandation : « Évite […] de rendre public un dépôt, un gist, un artifact ou un paquet. » |
| Nature | Recommandation (pas une interdiction) |
| Demande du builder | Garder le dépôt `IsoardiMarius/projetz` public. Le builder précise qu'il s'agit d'un projet personnel sur son compte GitHub personnel. |
| Risque expliqué | Tout ce qui est poussé dans le dépôt devient visible par tous et peut être copié ou indexé, même si on le supprime ensuite. Le projet traite des comptes Polymarket signalés comme anormaux : publier ces résultats exposerait à un risque de diffamation et de diffusion de données personnelles. |
| Décision | Le builder confirme : le dépôt reste public. |
| Mesures compensatoires | **Aucune donnée réelle n'est versionnée** : ni adresse suivie, ni transaction collectée, ni résultat d'analyse, ni dossier exporté. Les jeux de test sont fictifs. La liste des comptes suivis est stockée dans la base locale, pas dans le code. Le `.gitignore` exclut les fichiers d'environnement, les exports et les sauvegardes de la base. La fiche d'intention ne cite aucun identifiant de compte réel. |
