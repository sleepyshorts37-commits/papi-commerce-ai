# Mission 45 — Rapport final

## Objectif
Préparer le transfert du contenu mémoire et PAPI CHAT au moyen d'une charge utile locale liée au digest du bundle approuvé.

## Livrables
- `runtime/papi_core/sync_payload.py` : construction, validation, écriture et lecture des fichiers .papidata.
- `tests/test_sync_payload.py` : tests de liaison de contenu, confidentialité et intégrité de fichier.
- `docs/SYNC-CONTENT-PAYLOAD.md` : contrat et procédure.
- Prompt, plan, opérations, README et roadmap.

## Contrôles
- Correspondance exacte des IDs, types, séquences et empreintes SHA-256 au bundle.
- Mémoire limitée aux faits partagés normaux d'auteurs connus.
- Messages CHAT validés par le registre.
- Blocage de secrets et motifs courants de PII.
- Taille maximale de 2 Mio, canonisation, digest propre, permissions 0700/0600, écriture sans écrasement, liens symboliques refusés.

## Limites
Aucun import mémoire/CHAT, aucun transport réseau, aucun worker/scheduler, aucune activation ou déploiement. Les filtres PII ne sont pas exhaustifs; revue humaine requise. La vérification Ed25519 et l'anti-rejeu restent la responsabilité du récepteur Mission 44.

## Validation
À compléter après exécution des tests et vérification CI sur le SHA final exact.

## Gouvernance
PR en brouillon, ouverte et non fusionnée. Aucun secret, donnée client volontairement ajoutée, contact externe, publication, dépense ou paiement.
