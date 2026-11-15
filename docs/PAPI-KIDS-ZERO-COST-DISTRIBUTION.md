# PAPI KIDS — Distribution POD sans avance de trésorerie

## Objectif et règle non négociable

PAPI KIDS doit préparer et distribuer des livres sans demander au propriétaire d'avancer de l'argent. La politique de référence est `ZERO_UPFRONT_XOF`.

Cela signifie :
- aucun abonnement payant, frais d'inscription, achat de logiciel, publicité, commande d'échantillon ou stock financé par PAPI ;
- aucun paiement d'impression ou d'expédition par PAPI avant encaissement d'une commande ;
- aucune commande de livre d'auteur, preuve papier ou prototype physique sans autorisation et financement explicites ;
- aucun outil IA, API, police, image, modèle ou service payant ;
- aucun compte vendeur, contrat, publication ou engagement externe automatisé.

Une plateforme dont l'inscription est gratuite n'est pas automatiquement gratuite à exploiter. Les frais d'impression, commissions, frais de traitement, expédition, retenues, conversion de devise et seuils de versement doivent être comptabilisés. Le fait qu'un coût soit déduit du prix payé par le lecteur n'est acceptable que si PAPI n'a pas à le préfinancer et si la rémunération nette est positive et vérifiée.

## Plateformes dans le périmètre

| Plateforme | Modèle à évaluer | Risque principal à lever |
|---|---|---|
| Amazon KDP | Impression à la demande, ebooks | Éligibilité du vendeur depuis le Sénégal, versement, coût d'impression déduit des ventes, territoires et formats |
| Lulu | POD, vente directe et distribution | Moyen de versement utilisable au Sénégal, frais de production/expédition et nécessité éventuelle d'avancer le coût d'une commande |
| IngramSpark | POD et distribution librairies/bibliothèques | Conditions de compte, frais, délais et méthode de versement disponible au Sénégal |
| Bookvault | POD et fulfillment de boutique connectée | Financement des commandes connectées, coût unitaire, compte bancaire et seuils de paiement |
| Blurb | POD, livres illustrés et photo | Méthodes de versement, frais, coûts de production et disponibilité territoriale |
| Jumia Sénégal | Marketplace de livres physiques | Stock détenu par le vendeur ou stockage Jumia, coût d'impression local, commissions et logistique |

Ce tableau définit le périmètre d'étude ; il ne certifie pas qu'une plateforme accepte actuellement un vendeur domicilié au Sénégal ni qu'elle peut être utilisée sans avance de trésorerie.

## Règle de routage

Le moteur local `kids-channel-routing.py` ne consulte pas le réseau et n'invente aucun tarif. Il exige que chaque canal dispose de preuves pour les points suivants :

1. éligibilité du vendeur domicilié au Sénégal ;
2. versement effectivement accessible au Sénégal ;
3. livraison dans les territoires visés ;
4. compatibilité avec le format précis du livre ;
5. absence d'abonnement obligatoire ;
6. absence d'avance de fonds à chaque commande ;
7. absence de stock financé par PAPI ;
8. impression et fulfillment direct confirmés ;
9. coût initial total nul pour PAPI.

Résultats possibles :
- `ELIGIBLE_ZERO_UPFRONT` : tous les contrôles sont prouvés ; le canal peut être soumis à une revue humaine.
- `HOLD` : au moins une information est inconnue ; aucune recommandation automatique.
- `BLOCKED` : au moins une condition est incompatible avec le budget zéro.

Le moteur ne donne jamais l'autorisation de publier. Même un canal admissible reste soumis à la revue des droits, de la qualité, des fichiers, du prix, des marges, des conditions contractuelles et à l'accord humain.

## Politique particulière pour Jumia Sénégal

Le modèle marketplace physique est distinct du POD. Si le vendeur doit acheter ou imprimer des exemplaires avant la commande, le canal est bloqué par la politique zéro avance. Jumia Express n'est pas considéré comme gratuit sans preuve de l'absence de frais et de stock préfinancé. Une impression KDP ne satisfait pas automatiquement une commande Jumia.

Jumia pourra être réévalué si une solution contractuelle vérifiée permet la vente sans stock et sans avance de trésorerie par PAPI. Aucune telle solution n'est présumée.

## Produire des livres sans dépenses

- Rédaction, révision et préparation des briefs avec outils déjà disponibles et logiciels gratuits.
- Illustrations : privilégier les créations originales réalisables avec outils gratuits ; conserver la provenance et les licences. Ne pas utiliser de génération payante ni d'actifs sans droits clairs.
- Mise en page et export PDF avec outils gratuits ; contrôler les polices, images, fonds perdus, dimensions et profils couleur.
- Pas d'achat d'ISBN, de code-barres, de police, d'illustration, de modèle ou de service tant que l'option gratuite légale n'a pas été vérifiée.
- Ne pas commander d'exemplaire auteur ou d'épreuve payante. Les contrôles numériques doivent être exhaustifs avant toute éventuelle décision humaine de publication.
- Un livre gratuit à produire ne signifie pas qu'il est gratuit à expédier : les frais de fabrication doivent être supportés par la plateforme sur la commande client ou payés par le client, sans avance de PAPI.

## Vérifications à effectuer avant d'autoriser un canal

Pour chaque plateforme, collecter des preuves officielles datées et conserver :
- pays de résidence accepté et documents demandés ;
- méthodes de versement, banques et devises réellement prises en charge au Sénégal ;
- frais d'ouverture, abonnement, publication, ISBN et autres coûts ;
- qui paie l'impression, à quel moment et par quel moyen ;
- coût d'impression par format/page/couleur et prix minimum ;
- frais d'expédition, traitement, retours et réimpressions ;
- territoires et délais de livraison ;
- règles de droits, exclusivité, ISBN et distribution simultanée ;
- seuils, fréquence et délais de versement.

Les conditions peuvent évoluer. Un article de centre d'aide ou une page publique ne remplace pas une confirmation contractuelle dans le compte vendeur.

## État initial du registre

Les six profils sont présents dans `data/divisions/papi-kids-channel-profiles.json`. Les conditions Sénégal, versements, territoires, formats, frais et flux d'impression restent `unknown` jusqu'à vérification. Jumia est bloqué pour le routage zéro stock en raison du modèle de stock physique identifié dans la stratégie commerciale. Aucun canal n'est donc déclaré admissible dans cette version.

Commande locale en lecture seule :

```bash
python -m papi_core kids-channel-route --format paperback --country SN
```

Formats acceptés : `paperback`, `ebook`, `coloring_book`, `illustrated_book`, `activity_book`.

## Limites de la mission

La mission prépare un registre et un moteur de décision local. Elle ne crée pas de compte, ne contacte aucune plateforme, ne vérifie pas en direct les conditions actuelles, ne publie aucun livre, ne commande aucun exemplaire et ne déclenche aucune dépense. Les données inconnues restent explicitement inconnues.
