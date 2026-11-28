# Mission 204 — Création d'archives attachée aux descripteurs

Date : 2026-11-28

## Objectif

Fermer la fenêtre TOCTOU restante dans `create_verified_archive`. Après les Missions 201 à 203, la vérification et la restauration étaient attachées à des descripteurs épinglés, mais la lecture source et la création/publication de l'archive utilisaient encore des chemins re-résolus.

## État de départ vérifié

- Dépôt : `sleepyshorts37-commits/papi-commerce-ai`, branche par défaut `main`.
- `main` reste au SHA `34959b32eb99366c83d3b6e750ffd993fe4c0602`.
- Mission 202 : PR #379, brouillon ouverte et non fusionnée.
- Mission 203 : PR #380, brouillon ouverte et non fusionnée ; tête `19af5423b422f3847835d9a8458530df1df26830`.
- Les trois workflows de Mission 203 sont terminés avec succès : 259 tests Python, validation des registres et documentation.
- Aucun changement de `main`, aucune fusion ou déploiement.

## Changements

- Ouvre le parent du journal source composant par composant et lit les octets avec `_read_private_file_at`, sans re-résoudre le chemin du fichier.
- Vérifie le JSONL depuis les octets lus et exige un checkpoint courant correspondant exactement à la séquence et au hash de tête.
- Ouvre et valide le parent de destination, crée le dossier d'archive via `mkdir(dir_fd=...)`, puis l'ouvre avec `O_NOFOLLOW | O_DIRECTORY`.
- Écrit journal et manifeste par temporaires privés et liens matériels relatifs au descripteur d'archive ; aucun écrasement n'est autorisé.
- Synchronise le parent après création, le dossier après écriture et le parent après publication.
- Extrait la vérification en `_load_verified_archive_at` afin de vérifier le résultat par le descripteur déjà épinglé.
- Effectue le rollback relativement aux descripteurs ouverts ; ne retire le dossier que si son identité inode correspond encore au descripteur épinglé.
- Échoue fermé si les primitives `dir_fd`, liens matériels ou opérations de répertoire requises sont indisponibles.
- Ajoute des régressions pour les remplacements d'ancêtres côté source et destination, les échecs de synchronisation et la fermeture du temporaire.

## Validation

La validation GitHub Actions sera consignée après exécution sur la tête finale de cette PR. Les tests locaux ne sont pas exécutés dans cette session.

## Limites

- Le modèle suppose que les ancêtres et le système de fichiers sont des emplacements de confiance ; un processus de même UID qui contrôle le répertoire déjà ouvert reste hors périmètre.
- Les appels `fsync` locaux ne prouvent pas la persistance matérielle, la réplication, la sauvegarde hors site ni la durabilité d'un stockage distant.
- Aucun stockage WORM, chiffrement applicatif, rotation ou purge n'est ajouté.
- Aucun adaptateur d'ancrage de production n'est configuré ; les tests utilisent un adaptateur mémoire.

## Gouvernance

Branche dédiée empilée sur Mission 203 (#380). Aucun changement de `main`, aucune fusion, aucun déploiement, aucun agent/worker/scheduler activé, aucun secret, compte externe, paiement ou contact commercial.
