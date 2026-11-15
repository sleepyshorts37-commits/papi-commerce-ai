# Rapport Mission 80 — Routage PAPI KIDS zéro avance de trésorerie

## Objectif
Étendre PAPI KIDS à la distribution multicanale des livres papier et numériques, avec un principe impératif : aucun financement initial ou paiement par PAPI avant encaissement client. Le propriétaire ne doit pas avoir à acheter de stock, commander des épreuves, payer un abonnement, financer l'impression ou utiliser un service payant.

## Livrables
- `runtime/papi_core/kids_channel_routing.py` : moteur local de qualification des canaux avec états `ELIGIBLE_ZERO_UPFRONT`, `HOLD` et `BLOCKED`.
- `data/divisions/papi-kids-channel-profiles.json` : registre des six plateformes Amazon KDP, Lulu, IngramSpark, Bookvault, Blurb et Jumia Sénégal.
- `tests/test_kids_channel_routing.py` : tests des inconnues, coûts initiaux, avance par commande, stock, formats, doublons et absence de recommandation non prouvée.
- `docs/PAPI-KIDS-ZERO-COST-DISTRIBUTION.md` : politique détaillée, contrôles obligatoires, méthode de production gratuite et limites.
- CLI `kids-channel-route` : rapport local en lecture seule pour un format et un pays.
- Roadmap PAPI KIDS mise à jour.
- Correction d'un défaut de validation de date calendaire découvert par la CI dans le moteur de scoring Mission 79 (les dates impossibles comme 2026-02-31 sont désormais rejetées).

## Contrôles intégrés
Le moteur exige des preuves distinctes pour l'éligibilité d'un vendeur sénégalais, les versements au Sénégal, la couverture de livraison, les formats, l'absence d'abonnement, l'absence d'avance à chaque commande, l'absence de stock préfinancé, l'impression/fulfillment direct et le coût initial nul.

Toute valeur inconnue conduit à `HOLD`. Tout coût positif, stock requis, abonnement requis ou paiement préalable par le vendeur conduit à `BLOCKED`. Aucun résultat n'autorise la publication.

Le registre initial ne prétend pas connaître les conditions actuelles. Les cinq plateformes POD restent en attente de preuves officielles. Jumia est bloqué pour le modèle zéro stock sur la base du besoin de stock physique décrit dans la stratégie Mission 78.

## Vérification
Tests ajoutés : 11 tests unitaires ciblant les portes de décision et les refus conservateurs. La première exécution CI a révélé un défaut préexistant dans la validation des dates du scoring Mission 79 ; la validation calendaire a été corrigée dans cette branche. Les workflows doivent être réexaminés sur le SHA final avant de déclarer le lot validé.

## Hors périmètre
Aucun compte externe créé, aucune inscription, aucun contact, aucun contrat, aucun achat, aucune commande d'exemplaire, aucun stock, aucune publicité, aucune publication, aucune dépense, aucun agent activé et aucun déploiement.

## Limites restantes
- Les conditions des plateformes doivent être vérifiées à partir de sources officielles datées, notamment pour un vendeur domicilié au Sénégal.
- Les modalités de versement, coûts d'impression, frais d'expédition et besoins de trésorerie peuvent changer.
- Aucun canal n'est encore certifié admissible à zéro avance.
- Les droits, la qualité, les métadonnées, les marges et l'autorisation humaine restent des portes distinctes.
