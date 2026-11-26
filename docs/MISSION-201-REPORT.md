# Mission 201 — Parcours sûr des répertoires d'archives

## Date et objectif

26 novembre 2026. Réduire la course TOCTOU du parcours des chemins lors de l'inspection en lecture seule des archives d'audit.

## État de départ vérifié

- Dépôt public ; branche par défaut `main`.
- `main` : SHA `34959b32eb99366c83d3b6e750ffd993fe4c0602`.
- La lecture de `branches/main` indique `protected=false`, `protection.enabled=false` et aucun ruleset retourné. Aucune protection n'a été modifiée.
- Mission 200 : PR #377, ouverte, brouillon, non fusionnée, tête `7402888733509e632d24e467e150693e430f96df`, base #376.
- PR #362, #364 et #366 : ouvertes, brouillons, non fusionnées ; aucune revue ni aucun commentaire sur les PR examinées.
- PR #377 : aucune revue ni aucun commentaire au moment de l'inspection.

## Problème

Le lecteur vérifiait les composants parents par chemin puis ouvrait le parent avec une seule opération `open` utilisant `O_NOFOLLOW`. Ce drapeau protège le dernier composant ouvert, mais pas nécessairement les ancêtres résolus par le noyau pendant l'ouverture du chemin complet. Un remplacement d'ancêtre par un lien symbolique entre le contrôle et l'ouverture pouvait donc rediriger l'inspection.

## Changements

- Ajoute `_open_directory_chain`, qui ouvre le point de départ puis chaque composant relativement au descripteur précédent avec `O_DIRECTORY | O_NOFOLLOW`.
- Garde les descripteurs ouverts pendant la descente ; l'inspection de la cible et le scan restent relatifs au descripteur du parent déjà ouvert.
- Remplace le contrôle path-based suivi d'une ouverture unique dans `inspect_archive_recovery`.
- Ajoute un test de régression qui remplace un ancêtre par un lien symbolique juste avant l'ouverture du composant enfant. L'inspection doit rester attachée au répertoire déjà ouvert et ne pas basculer vers l'arbre de l'attaquant.
- Documente le mécanisme et ses limites ; ajoute une entrée dédiée dans la roadmap.

## Fichiers modifiés

- `runtime/papi_core/audit_archive.py`
- `tests/test_audit_archive.py`
- `docs/AUDIT-ARCHIVES.md`
- `docs/ROADMAP.md`
- `docs/MISSION-201-REPORT.md`

## Validation GitHub Actions

SHA de code validé : `f582805524efa33d8d368d4f033c33fb031fc659`.

- [PAPI core tests — run #2874](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45822408064) : succès, **256 tests exécutés, 256 réussis, 0 échec**. Le nouveau test `test_inspection_pins_parent_before_ancestor_is_replaced` est explicitement `ok`.
- [PAPI registry validation — run #934](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45822408018) : succès.
- [PAPI documentation checks — run #901](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45822407932) : succès.
- `pip check` : aucun conflit de dépendances.
- Deux contrôles `pip-audit` : aucune vulnérabilité connue détectée dans les graphes analysés.
- PostgreSQL 16 jetable : initialisation, schéma, fixtures legacy, migration des tentatives, concurrence `SKIP LOCKED` et rollback : succès.
- Tests locaux : non exécutés ; la validation provient de GitHub Actions.

## Limites

- Le parcours exige `O_NOFOLLOW`, `O_DIRECTORY` et l'ouverture relative par descripteur ; les plateformes ne fournissant pas ces primitives échouent fermé.
- La protection réduit la course de remplacement symbolique des composants déjà ouverts. Elle ne protège pas contre un acteur qui contrôle les répertoires, les permissions, les montages ou le système de fichiers.
- Aucun test de panne matérielle, coupure d'alimentation, stockage distant, réplication ou WORM n'est revendiqué.
- L'inspection reste en lecture seule ; aucun temporaire n'est promu, renommé ou supprimé.

## Gouvernance

PR #378 en brouillon, empilée sur #377. Aucun changement direct de `main`, aucune fusion, aucun déploiement, aucune base de production, aucun worker ou agent réel activé, aucun secret manipulé, aucun compte externe utilisé, aucun paiement, transfert ou contact commercial.
