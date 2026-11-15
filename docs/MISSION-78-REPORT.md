# Rapport Mission 78 — Validation commerciale et Jumia Sénégal

## Réalisations
- Ajout de `docs/PAPI-KIDS-COMMERCIAL-STRATEGY.md` : processus de validation de demande, segmentation acheteur/utilisateur, tests à faible coût, critères GO/REWORK/STOP, chaîne de commercialisation complète, indicateurs et calcul de marge.
- Formalisation de deux circuits séparés : Amazon KDP impression à la demande et vente de livres physiques sur Jumia Sénégal.
- Recherche de pages officielles Jumia VendorHub : inscription/KYC, formation, logistique Dropship vs Jumia Express, barème 2026.
- Mise à jour de `docs/PAPI-KIDS-PUBLISHING.md` et `docs/ROADMAP.md`.

## Constat important sur Jumia
La page de commissions 2026 consultée (datée du 21 janvier 2026) indique 20 % pour la catégorie Livres. Ce taux doit être reconfirmé avant tarification ; il ne comprend pas nécessairement tous les frais de livraison/traitement. Le KYC publié demande des justificatifs d'identité et fiscaux, un compte bancaire et une attestation bancaire avec IBAN. La FAQ indique une formation obligatoire. Les conditions exactes de catégorie, versement et frais doivent être validées directement dans Vendor Center.

Le modèle Jumia nécessite un stock physique détenu par le vendeur en Dropship, ou remis à Jumia dans le cadre de Jumia Express. Il ne faut pas confondre ce circuit avec l'impression à la demande KDP : une commande Jumia ne déclenche pas l'impression Amazon. La vente Jumia peut donc exiger un petit tirage local ou autre approvisionnement physique, et comporte un risque de stock.

## Principes anti-risque
- Étudier la demande avant de produire le livre entier.
- Tester des concepts auprès d'adultes, sans encaisser de précommandes à ce stade.
- Calculer la marge nette par canal avant de fixer les prix.
- Démarrer Jumia uniquement après vérification de l'éligibilité, des frais complets et d'un pilote de stock limité autorisé.
- Aucune promesse de ventes garanties.

## Limites
Mission documentaire et recherche publique uniquement. Aucun compte Jumia ou KDP créé, aucune inscription soumise, aucun client contacté, aucune annonce publiée, aucun stock acheté, aucune publicité et aucune dépense. Aucun agent n'a été activé.

## Tests
Aucun test logiciel n'a été ajouté ou exécuté pour ces changements documentaires. Les workflows CI devront être contrôlés sur le SHA final après ouverture de la PR.
