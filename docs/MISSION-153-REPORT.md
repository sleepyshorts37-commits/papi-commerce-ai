# Mission 153 — Test de restauration isolé

## Livrable
- Déchiffre et authentifie une sauvegarde AES-256-GCM avant toute restauration.
- Exige \`restore_authorized=True\`, un nom de base explicitement confirmé et un suffixe \`_restore_test\` ou \`_drill\`.
- Refuse une base identique à \`PAPI_KIDS_DATABASE_URL\`.
- Exécute \`pg_restore\` avec transaction unique, \`--exit-on-error\`, sans secrets dans argv, et délai borné.
- Nettoie le fichier déchiffré temporaire.
- Erreurs expurgées, aucun détail SQL sensible.
- Tests simulés d'autorisation, d'isolement et d'absence de fuite des identifiants.

## Limites
Aucune restauration réelle n'a été exécutée. Le test réel exige une base PostgreSQL jetable, explicitement créée pour le drill, et une autorisation opérateur. Le service ne crée pas ni ne supprime cette base.
