# Mission 39 — Validation exécutable des paquets de synchronisation

## Objectif
Transformer le contrat préparé en Mission 38 en un premier composant exécutable local : construction et validation d'une enveloppe de synchronisation référentielle, sans transport ni import de contenu.

## Jour 1 — Contrat et modèle de menace
- Reprendre le contrat de Mission 38 et définir le périmètre minimal des métadonnées transférables.
- Exclure corps de messages, contenus mémoire, données client, secrets et clés.

## Jour 2 — Canonisation et intégrité
- Implémenter une sérialisation JSON canonique et SHA-256.
- Valider version de protocole, identités source/destination, export ID et horodatage zoné.

## Jour 3 — Cohérence du journal
- Valider les événements référentiels autorisés, leurs empreintes, identifiants et séquences.
- Rejeter doublons, séquences non contiguës, plage incorrecte, type inconnu et dépassement de taille.

## Jour 4 — Tests adversariaux
- Tester altération, mauvaise destination, version inconnue, curseurs, doublons, dates sans fuseau et paquets vides.
- Vérifier que le validateur ne peut ni importer ni écrire des données.

## Jour 5 — Documentation et livraison
- Documenter limites et intégration future; mettre à jour la roadmap.
- Exécuter CI sur le SHA final et ouvrir une PR brouillon non fusionnée.

## Critères d'acceptation
- Module Python indépendant avec construction et validation déterministes.
- Enveloppe référentielle sans contenu métier.
- Digest SHA-256 recalculé et comparaison de destination possible.
- Séquences contiguës et événements uniques; validation fail-closed.
- Tests unitaires et CI réussis sur le SHA final.

## Hors périmètre
Signature propriétaire, import transactionnel, transport réseau, synchronisation réelle, Supabase distant, déploiement, worker/scheduler, communication externe et opérations financières.