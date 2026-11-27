# Mission 202 — Lecture vérifiée des archives par descripteurs

## Date et objectif

27 novembre 2026. Étendre aux opérations de vérification et de restauration la protection par descripteurs introduite pour l'inspection en lecture seule lors de la Mission 201.

## État de départ vérifié

- Dépôt : `sleepyshorts37-commits/papi-commerce-ai`, branche par défaut `main`.
- `main` reste au SHA `34959b32eb99366c83d3b6e750ffd993fe4c0602` ; aucun changement n'y est effectué.
- Mission 201 : PR #378, ouverte, brouillon, non fusionnée ; tête `2fec98d29d85dff29b731bf033e0752ba70c05cb`, base #377.
- Les trois workflows de Mission 201 sont terminés avec succès : 256 tests Python, validation des registres et documentation.
- Les PR historiques restent ouvertes et non fusionnées ; aucune revue ni fusion n'est effectuée pendant cette mission.

## Problème traité

L'inspection de récupération utilisait désormais des descripteurs épinglés, mais le chargement d'une archive par `verify_archive` et par la restauration reposait encore sur des contrôles de chemin suivis d'ouvertures path-based. Le remplacement d'un ancêtre pouvait donc rediriger la lecture de l'archive avant que les contrôles de contenu ne s'appliquent.

## Changements

- Ajoute `_open_archive_directory` : ouvre chaque parent par descripteur relatif, puis ouvre le dossier d'archive depuis le parent épinglé.
- Ajoute `_read_private_file_at` : ouvre manifeste et journal relativement au descripteur du dossier avec `O_NOFOLLOW`, contrôle type, propriétaire, permissions, taille et stabilité des métadonnées pendant la lecture.
- Refactorise `_load_verified_archive` pour lister et lire les deux fichiers par descripteur. `verify_archive` et la vérification préalable de `restore_verified_archive` bénéficient de cette lecture épinglée.
- Ferme le descripteur dans `_open_inspection_directory` même si `fstat` échoue, et convertit cette erreur système en erreur d'archive contrôlée.
- Ajoute deux tests : remplacement d'un ancêtre par un lien symbolique pendant la descente, et fermeture du descripteur après échec de `fstat`. Le test de course ne saute que si la plateforme ne permet pas de créer un lien symbolique ; les erreurs de vérification ne sont pas transformées en skip.
- Actualise la documentation des archives et la roadmap.

## Validation GitHub Actions

Code et tests validés sur le SHA `1e29f0a7ae5480388caa4a3c1137d78c55a8b616` :

- [PAPI core tests — run #2877](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45966752097) : succès, **258 tests exécutés, 258 réussis, 0 échec**. Les deux nouveaux tests sont explicitement `ok`.
- [PAPI registry validation — run #937](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45966752226) : succès.
- [PAPI documentation checks — run #904](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45966752224) : succès.
- `pip check` : `No broken requirements found`.
- Deux audits `pip-audit` : `No known vulnerabilities found`.
- PostgreSQL 16 jetable : initialisation, schéma, fixtures legacy, migration des tentatives durables, concurrence `SKIP LOCKED` et rollback : succès.
- Tests locaux : non exécutés ; la validation provient des workflows GitHub Actions.

Le commit de documentation de ce rapport est postérieur au SHA de code testé ; il ne modifie ni le runtime ni les tests.

## Limites

- La protection empêche la re-résolution des chemins après ouverture des descripteurs ; elle ne protège pas contre un acteur qui contrôle le contenu du répertoire déjà ouvert, les permissions, les montages ou le système de fichiers.
- La création des archives et la publication de la destination de restauration conservent leurs contrôles path-based actuels ; elles feront l'objet d'une revue distincte.
- Aucun test de panne matérielle, coupure d'alimentation, stockage distant, réplication ou WORM n'est revendiqué.

## Gouvernance

PR #379 en brouillon, empilée sur #378. Aucun changement de `main`, aucune fusion, aucun déploiement, aucun agent/worker/scheduler activé, aucun secret, compte externe, paiement ou contact commercial.
