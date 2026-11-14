# Mission 40 — Rapport final

## Objectif
Authentifier une approbation propriétaire pour un paquet référentiel exact, sans activer de synchronisation.

## Livrables
- `runtime/papi_core/sync_bundle_approval.py` : signature et vérification Ed25519 d'une attestation liée au digest SHA-256, à la source, à la destination, à l'export et aux identifiants ordonnés.
- Contrôle du scope, du propriétaire, de la destination, de la fenêtre temporelle et du TTL.
- Réutilisation du registre de clés publiques et de l'anti-rejeu SQLite local.
- `tests/test_sync_bundle_approval.py` : tests de validité, altération, portée, identité, durée et rejeu.
- Documentation opérateur, prompt et plan cinq jours.

## Limites
Aucun import, transport, registre distribué de nonces, consommation du ledger SQL partagé, déploiement, worker, scheduler ou synchronisation réelle. L'anti-rejeu est local à une installation. La vérification ne prouve pas la légitimité juridique du titulaire.

## Validation
CI réussie : run #1228 (`43616441468`) sur le SHA `31c785e457f178036b21e7349c99752395cd834c`. Les deux jobs (`tests` et `local-postgrest-integration`) sont au vert; 391 tests Python réussis.

## Gouvernance
Aucune clé privée, donnée client ou secret n'est ajouté au dépôt. PR brouillon, ouverte et non fusionnée.
