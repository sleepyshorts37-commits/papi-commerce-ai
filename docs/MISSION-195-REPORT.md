# Mission 195 — Détecter les collisions d'identifiants d'événements d'audit

## Objectif
Refuser la réutilisation d'un `event_id` pour un contenu sémantique différent, au lieu de traiter toute collision comme un retry idempotent.

## Changements
- Lorsqu'un `event_id` existe déjà, comparer le payload sémantique en excluant `occurred_at` et les champs de chaîne calculés.
- Retourner `False` uniquement pour un retry équivalent ; lever `AuditError` si acteur, action, entité ou détails diffèrent.
- Ajouter deux régressions : retry équivalent avec timestamp différent et collision de payload sans modification du journal.
- Actualiser la documentation et la roadmap.

## Validation vérifiée
Code testé sur le SHA `0fafd5dd3413fac7aae2d626fdfc0b4fbc5109ca` :
- [PAPI core tests — run 45181295109](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45181295109) : succès, **234 tests**, 0 échec.
- [PAPI registry validation — run 45181294898](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45181294898) : succès.
- [PAPI documentation checks — run 45181294883](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45181294883) : succès.
- `pip check` : aucun conflit.
- `pip-audit --strict -r requirements.txt` et audit de l'environnement scanner : aucune vulnérabilité connue.
- PostgreSQL 16 jetable : schéma, migration, historique, reprise/statuts, concurrence `SKIP LOCKED` et rollback réussis.
- Tests locaux : non exécutés.

Le rapport est ensuite ajouté au commit documentaire. La CI doit être confirmée sur la tête mise à jour qui inclut ce rapport.

## État de la PR
- PR #372 : brouillon, ouverte, non fusionnée.
- Base : Mission 194 (#371), SHA `7a5eb8e3b6f4c65268af817d940f65c7768aaea3`.
- Branche : `mission-195-audit-event-id-collision`.
- 5 commits, 5 fichiers ; aucun conflit signalé au dernier contrôle.
- Aucune revue ni commentaire enregistré.

## Gouvernance
Aucun changement sur `main`, aucune fusion ou déploiement. Aucun agent/worker activé, aucune intégration externe, secret, compte, paiement, transaction ou contact externe.
