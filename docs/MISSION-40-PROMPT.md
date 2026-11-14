# Mission 40 — Authentification des paquets de synchronisation

## Objectif
Ajouter une approbation propriétaire Ed25519 liée au digest exact d'un paquet référentiel de Mission 39, avec destination, export, événements ordonnés, durée de validité et protection anti-rejeu.

## Jour 1 — Audit et modèle de menace
- Réutiliser le registre Ed25519, la rotation/révocation et le vérificateur anti-rejeu existants.
- Définir un scope exclusif à l'approbation d'un paquet; exclure toute clé privée et tout secret du dépôt.

## Jour 2 — Attestation signée
- Créer un payload canonique liant digest, source, destination, export et liste ordonnée des événements.
- Imposer décision explicite, identifiant d'approbation et dates zonées.

## Jour 3 — Vérification fail-closed
- Vérifier identité propriétaire, signature, destination attendue, intégrité du paquet, scope et TTL.
- Rejeter toute altération, expiration, durée excessive ou rejeu.

## Jour 4 — Tests adversariaux
- Couvrir signature valide, mauvaise identité, digest/destination/scope/événements modifiés, TTL, paquet altéré et rejeu.
- Vérifier qu'aucun import ni effet métier n'est déclenché.

## Jour 5 — Documentation et livraison
- Ajouter contrat opérateur et rapport; préciser les limites de l'anti-rejeu local.
- Exécuter CI sur le SHA final et ouvrir une PR brouillon non fusionnée.

## Critères d'acceptation
- Fonctions locales de signature et vérification Ed25519.
- Approbation liée cryptographiquement au paquet exact.
- Anti-rejeu, destination et fenêtre de validité contrôlés.
- Tests et CI réussis sur le SHA final.

## Hors périmètre
Transport réseau, import transactionnel, registre de nonce distribué, consommation SQL distante, migration, déploiement, activation de worker/scheduler, communication externe et paiements.
