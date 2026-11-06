# Radar — analyse personnelle de Polymarket

Outil personnel qui observe Polymarket et sert à quatre choses :

- repérer les **flux informés**, c'est-à-dire des comptes qui parient comme s'ils savaient ;
- **cartographier les liens** entre wallets ;
- **croiser** ces observations avec d'autres données ;
- **évaluer des stratégies en paper trading** (trading fictif aux prix réels).

Cadrage complet : [`docs/cahier_des_charges.md`](docs/cahier_des_charges.md). Étude préalable : [`docs/etude/`](docs/etude/).

## État

**Phase 0 en cours** : étude de données sur des cas connus et sur un échantillon large. Elle doit répondre à une question : *un détecteur aurait-il repéré les initiés à temps, et restait-il un avantage à les suivre ?*

## Démarrage (développement)

Prérequis :
- [uv](https://docs.astral.sh/uv/) ;
- un PostgreSQL accessible.

```bash
uv sync
export RADAR_DATABASE_URL="postgresql://user@localhost:5432/radar"   # ne jamais versionner d'identifiants
uv run radar migrate
uv run radar collect-market --condition 0x...           # tous les trades d'un marché
uv run pytest                                           # tests
uv run ruff check . && uv run mypy                      # qualité
```

## Données et vie privée

- **Sources** : uniquement des API publiques (Polymarket Data API v2, Gamma, blockchain Polygon).
- **Données traitées** : adresses de wallets pseudonymes et transactions publiques. Ni bio ni photo de profil n'est conservée, et aucun rapprochement n'est fait avec une identité réelle.
- **Usage** : strictement personnel. Les données et les résultats restent dans la base locale ou privée. **Aucune donnée réelle n'est versionnée** dans ce dépôt, qui est public.
- **Interprétation** : un signal de « flux informé » est une observation statistique sur un comportement de trading. Ce n'est ni une accusation ni une preuve.
- **Légalité** : prendre des positions sur Polymarket depuis la France n'est pas autorisé (ANJ). L'outil fonctionne donc en observation et en paper trading.
