# Contrat de synchronisation PAPI CHAT et mémoire — version 0.1 (préparation)

## Statut
Spécification de sécurité pour implémentation locale ultérieure. Aucun transport réseau ni synchronisation réelle n'est fourni ou activé par ce document.

## Enveloppe conceptuelle
Un paquet doit contenir :
- `protocol_version` : version majeure/mineure reconnue;
- `source_instance_id` et `destination_instance_id` : identifiants stables inscrits au registre;
- `export_id` : UUID unique;
- `created_at` : ISO-8601 avec offset;
- `cursor_start` et `cursor_end` : bornes non ambiguës;
- `events` : liste bornée d'événements autorisés et validés;
- `payload_digest` : SHA-256 sur la sérialisation canonique sans le champ digest;
- `approval_proof` : preuve liée au digest, aux deux instances, à la portée et à l'ordre exact des IDs.

Ce schéma est normatif pour la conception, pas encore un format exécutable. La canonisation, les tailles maximales et les signatures doivent être fixées dans le code avant d'accepter un paquet.

## Invariants
- Source et destination doivent être distinctes, reconnues et explicitement autorisées.
- Chaque événement conserve son ID d'origine, son acteur, son horodatage zoné, son type et son digest.
- Les événements CHAT et mémoire ne sont pas interchangeables; chacun suit sa validation métier existante.
- Import atomique : prévalidation complète avant toute mutation; échec = zéro événement importé.
- Même ID + même digest : doublon idempotent, ignoré et audité.
- Même ID + digest différent : conflit bloquant, jamais écrasé.
- Curseur discontinu, export incomplet, version inconnue, signature invalide ou approbation périmée : rejet fail-closed.
- Une approbation ne peut être réutilisée; les nonces doivent être consommés atomiquement dans un stockage partagé.
- Pas de fusion automatique des conflits de contenu ni d'effacement d'historique append-only.

## Confidentialité et gouvernance
Exclure les credentials, clés privées, données client et événements restreints. L'accès à un canal doit être autorisé indépendamment de la possession d'un paquet. L'approbation propriétaire est nécessaire avant toute activation d'un transport ou sync réelle.

## Tests nécessaires avant exploitation
Fixtures synthétiques multi-instances; export/import idempotent; reprise après interruption; événement répété; ID divergent; digest altéré; ordre/cursor invalides; source/destination non autorisées; signature/nonce invalide; paquet mixte contenant une entrée invalide et preuve d'absence de mutation partielle; compatibilité de version; backup/restore.

## Limites connues
Un protocole écrit ne constitue pas une implémentation. PAPI CHAT et mémoire restent locaux, et les garanties de verrouillage, transaction multi-instance, confidentialité en transit et disponibilité ne sont pas établies ici.