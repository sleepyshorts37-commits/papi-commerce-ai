# Mission 168 — Enregistrement versionné des métadonnées KDP

## Livrable
- Migration PostgreSQL 018 : historique append-only des versions de fiche KDP, RLS, accès service_role.
- Endpoint HTTPS \`POST /api/papi-kids/manuscripts/{upload_id}/kdp-metadata\`, avec jeton distinct \`PAPI_KIDS_METADATA_TOKEN\`.
- Identité éditeur issue de \`PAPI_KIDS_METADATA_EDITOR_ID\`, jamais du navigateur.
- Les brouillons incomplets sont acceptés et enregistrés avec les blocages de validation ; aucune donnée manquante n'est inventée.
- SHA-256 canonique, numéro de version, état de validation et identité de l'éditeur conservés.
- Le status API expose la dernière version du brouillon.
- Tests endpoint, transaction PostgreSQL, migration SQL, version et blocages.

## Gouvernance
Enregistrer une fiche ne l'approuve pas et n'autorise pas l'upload. Chaque version reste distincte et le release gate exige toujours la cohérence des métadonnées.
