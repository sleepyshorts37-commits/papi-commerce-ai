# Mission 173 — Persistance des packages KDP fabriqués

## Livrable
- Migration PostgreSQL 019 : journal append-only des packages KDP (version, manifeste JSON, SHA-256, statut).
- Après fabrication locale, le service persiste le manifeste dans PostgreSQL et met à jour les métadonnées du livre.
- Si l'enregistrement DB échoue, le dossier de package créé par cette tentative est supprimé pour éviter un résultat orphelin.
- Le status API expose le dernier package et son statut au tableau de bord iPhone.
- Tests de transaction, hash du manifeste, status reader et RLS.

## Gouvernance
La persistance ne vaut pas validation du PDF ou de l'EPUB. Les états restent en attente d'inspection manuelle/Kindle Previewer ; aucune soumission ou publication n'est activée.
