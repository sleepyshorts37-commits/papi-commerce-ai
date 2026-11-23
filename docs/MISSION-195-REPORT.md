# Mission 195 — Déduplication d'audit avec détection des collisions

## Objectif
Éviter qu'un même `event_id` soit silencieusement accepté pour deux événements de contenu différent.

## Changements
- Lorsqu'un `event_id` existe déjà, comparer le payload sémantique en excluant `occurred_at` et les champs de chaîne calculés.
- Retourner `False` uniquement pour un retry équivalent ; lever `AuditError` si acteur, action, entité ou détails diffèrent.
- Ajouter deux régressions : retry équivalent avec timestamp différent et collision de payload sans modification du journal.
- Actualiser la documentation et la roadmap.

## Validation
- Tests locaux : non exécutés.
- CI : en attente du SHA de cette branche.
- Aucune intégration externe ni base de production utilisée.

## Gouvernance
PR brouillon empilée sur Mission 194 (#371). Aucun changement sur `main`, aucune fusion ou déploiement. Aucun agent/worker, secret, compte, paiement, transaction ou contact externe activé.
