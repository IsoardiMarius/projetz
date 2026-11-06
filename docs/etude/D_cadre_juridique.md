# Polymarket : cadre juridique avant de construire (au 6 nov. 2026)

**Hypothèse :** résident fiscal français (à confirmer), usage personnel. **[F]** = fait sourcé, **[I]** = interprétation. Ce n'est pas un avis juridique.

## 1. Polymarket en France

- [F] **Nov. 2024 :** géoblocage après intervention de l'ANJ ([anj.fr](https://anj.fr/suite-lintervention-de-lanj-le-site-polymarket-ne-propose-plus-ses-services-sur-le-territoire)). **24 févr. 2026 :** l'ANJ qualifie les plateformes de prédiction de « sites de jeux d'argent illégaux » ([anj.fr](https://anj.fr/plateformes-de-marches-de-prediction-des-sites-illegaux-en-france-qui-peuvent-presenter-des-risques)).
- [F] **16-17 juil. 2026 :** blocage de polymarket.com par les FAI, sur ordre de l'ANJ ([anj.fr](https://anj.fr/promotion-dune-offre-de-jeux-dargent-illegale-blocage-du-site-polymarket)). Motifs : promotion d'une offre illégale, absence de KYC, enquête du parquet de Paris (4 mai 2026) sur des paris météo. Polymarket a formé un recours (21 août) ; aucune décision trouvée.
- [F] **CGU** (11 août 2026, [polymarket.com/tos](https://polymarket.com/tos)) : France restreinte ; VPN « strictly prohibited » ; sanctions : wallet en « close-only », résiliation ; pas de clause de confiscation ; scraping interdit (§ 4.2). France en « close-only » sur le site et l'API ([geoblock](https://docs.polymarket.com/api-reference/geoblock)).
- [I] **Risque pour le joueur :** aucun texte trouvé ne sanctionne le simple joueur. Le Code de la sécurité intérieure (L. 320-1 s.) vise l'offre et la publicité. L'ANJ rappelle que diffuser les cotes d'un site non agréé dans un but promotionnel est puni de 100 000 €. L'amende de 100 000 € « pour VPN » relayée par la presse (KultureGeek, 24 août) ne cite aucun texte. Risques réels : fonds bloqués, aucun recours, questions des PSAN sur l'origine des fonds.
- [F] **Polymarket US** (CFTC) : « Built for US residents ». L'inscription exige une adresse et un numéro de sécurité sociale américains ([docs.polymarket.us](https://docs.polymarket.us/learn/get-started/signup)). Inaccessible en pratique.

## 2. Alternatives

- [F] En France, l'offre agréée par l'ANJ se limite aux paris hippiques et sportifs : aucun pari politique. [I] Betfair Exchange ne semble pas agréé (à vérifier).
- [F] Kalshi géobloque la France (ANJ, févr. 2026 ; liste dans son *Member Agreement*).
- [F] **ESMA, 3 juil. 2026 :** un contrat d'événement qui est un instrument financier est probablement une option binaire, interdite à la vente aux particuliers ([esma.europa.eu](https://www.esma.europa.eu/press-news/esma-news/esma-reminds-firms-existing-rules-and-obligations-under-binary-option-measures)).
- [I] Aucune alternative équivalente ; reste le *paper trading*.

## 3. Délit d'initié

- [F] **CFTC, avis du 25 févr. 2026 :** trader avec une information confidentielle détournée en violation d'un devoir de confiance (*misappropriation*) viole CEA § 6(c)(1) et la règle 180.1 ([9185-26](https://www.cftc.gov/PressRoom/PressReleases/9185-26)). Le 31 mars, le directeur de l'Enforcement annonce poursuivre « ceux qui transmettent ou négocient » ces informations ([discours](https://www.cftc.gov/PressRoom/SpeechesTestimony/opamiller1)).
- [F] **Maduro :** le 23 avr. 2026, la CFTC et le SDNY poursuivent un militaire (plus de 404 000 $ de gains), premier dossier d'initié sur contrats d'événements ([9217-26](https://www.cftc.gov/PressRoom/PressReleases/9217-26)). **Iran :** le 12 févr. 2026, Israël inculpe un réserviste et un civil. Aucune poursuite publique trouvée pour les wallets des frappes du 28 févr. 2026.
- [F] **Polymarket :** ses CGU (§ 4.2) interdisent de trader sur une information confidentielle. Sa page [Transparence](https://polymarket.com/transparency) (18 août 2026) prévoit la restriction de wallets et le signalement aux autorités. En avril 2026, Polymarket a audité les applications de *copy-trading* qui promettaient de « trouver les initiés » (The Block).
- [I] **Copier des positions publiques :** la responsabilité du *tippee* (*Dirks*, *Salman*) suppose de recevoir sciemment une information non publique d'un initié fautif. Une transaction on-chain est publique : le copieur « pur » ne semble pas exposé. Un contact, une entente ou un partage de gains change l'analyse. Restent la clause « abusive, improper » des CGU et une compétence américaine extraterritoriale incertaine.
- [I] **France/UE :** MAR (art. 2) vise les instruments négociés sur une plateforme de l'UE ; le titre VI de MiCA (art. 86) vise les crypto-actifs admis sur une plateforme agréée ([MAR](https://eur-lex.europa.eu/eli/reg/2014/596/oj), [MiCA](https://eur-lex.europa.eu/eli/reg/2023/1114/oj)). Polymarket ne relève ni de l'un ni de l'autre, ni de l'art. L. 465-1 du CMF : MAR probablement inapplicable.

## 4. Fiscalité

- [F] Les gains de jeux de hasard ne sont pas imposables, « même » habituels ([BOI-BNC-CHAMP-10-10-20-40 § 400](https://bofip.impots.gouv.fr/bofip/2824-PGP.html/identifiant=BOI-BNC-CHAMP-10-10-20-40-20190902)). Une activité d'habileté organisée peut l'être en BNC (art. 92 CGI).
- [F] **Actifs numériques** (art. 150 VH bis CGI) : imposition à la conversion en euros ; échanges entre crypto-actifs en sursis ; exonération si les cessions totalisent 305 € par an au plus ; taux forfaitaire de 31,4 % en 2026 selon la presse (à confirmer). L'achat-revente habituel relève des BNC depuis 2023 (LF 2022, art. 79).
- [I] Les parts Polymarket sont des jetons réglés en USDC : imposition probable à la conversion en euros. Un outil automatisé accroît le risque de requalification en BNC. Prévoir un rescrit (art. L. 80 B LPF) ou un fiscaliste.
- [F] **3916-bis :** obligatoire pour les comptes d'actifs numériques ouverts auprès d'un prestataire étranger (art. 1649 bis C CGI). [I] Amende : 750 € par compte, 1 500 € au-delà de 50 000 € (art. 1736 X CGI, à vérifier). Le wallet Polymarket est non hébergé et a priori exclu (lecture dominante, non confirmée) ; l'exchange étranger utilisé doit être déclaré.

## 5. RGPD

- [F] L'art. 2.2.c et le considérant 18 excluent les traitements strictement personnels. *Lindqvist* (C-101/01, 6 nov. 2003) : une publication accessible à tous sort de l'exemption. *Ryneš* (C-212/13, 11 déc. 2014) : interprétation stricte.
- [F] Une adresse de wallet est une donnée personnelle si la personne est identifiable (EDPB, lignes directrices 02/2025). L'identifiabilité s'apprécie selon les moyens raisonnables (CJUE, *EDPS c/ SRB*, C-413/23 P, 4 sept. 2025).
- [I] L'analyse locale pour soi relève plausiblement de l'exemption. Elle tombe en cas de publication de scores ou de listes d'« initiés », de dépôt GitHub public avec données ou résultats, de partage ou d'enrichissement d'identité (ENS, X, Arkham). Désigner publiquement une personne identifiable comme initiée expose aussi à la diffamation (loi de 1881).

## 6. AI Act

- [F] **Art. 2.10 :** exclut les obligations du déployeur pour une activité « purement personnelle non professionnelle ». Les lignes directrices de la Commission (C(2025) 884, 4 févr. 2025, § 34-35) précisent : une activité qui procure un avantage économique « de manière régulière » est professionnelle ; une activité criminelle n'est jamais personnelle ; le fournisseur (celui qui publie l'outil) reste soumis au règlement.
- [F] **Art. 5.1.d :** ses conditions sont cumulatives : un système d'IA évalue le risque qu'une personne physique commette une infraction pénale, sur la seule base du profilage. Selon les lignes directrices, l'évaluation est tournée vers l'avenir (§ 191) ; des faits objectifs et « substantiels » écartent le critère « seule base » (§ 202) ; un acteur privé qui protège ses intérêts, le risque pénal restant accessoire, est hors champ (§ 210-211).
- [I] Un score fondé sur des faits de marché (âge du wallet, timing, taille, réussite) paraît hors de l'art. 5.1.d : des règles écrites à la main ne forment peut-être pas un « système d'IA », et le score vise un avantage informationnel sur des faits objectifs. Le risque monte si l'outil se présente comme détecteur de délinquants, cible des personnes identifiées ou est publié. L'exemption 2.10 devient douteuse si les gains sont réguliers. Le socle de l'organisation interdit, sans arbitrage, toute IA relevant de l'art. 5 : présenter le score comme un « signal de marché ».

---

> **Clairement permis** [I] : lire les données on-chain (Polygon), analyser localement pour soi, backtest et *paper trading*, code sans données (un dépôt public reste déconseillé par le socle de l'organisation).
>
> **Zone grise :** utiliser les API Polymarket (scraping interdit par les CGU) ; qualifier fiscalement les gains ; invoquer l'art. 2.10 avec des gains réguliers ; enrichir l'identité des wallets ; copier des wallets suspects (a priori licite pénalement ; CGU floues).
>
> **Clairement risqué :** trader sur Polymarket depuis la France (illégal selon l'ANJ, VPN interdit, fonds bloquables) ; publier des listes d'« initiés », des scores ou des cotes ; dépôt public avec données ; tout contact avec un compte copié ; omettre le 3916-bis ou les plus-values.
>
> **Avocat ou fiscaliste nécessaire :** risque pénal du joueur, qualification fiscale, exposition aux autorités américaines.
