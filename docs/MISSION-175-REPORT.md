# Mission 175 — Inspection humaine et téléchargement sécurisé des fichiers KDP

## Livrable
- Migration PostgreSQL 020 : journal append-only des revues PDF/EPUB, RLS, hash, réviseur, date, décision et notes.
- Endpoint HTTPS pour enregistrer une revue liée à la version et au SHA-256 du dernier package.
- Endpoint de téléchargement privé des PDF/EPUB avec vérification SHA-256, chemin confiné au stockage privé, rejet des symlinks et traversées de chemin.
- Téléchargement PDF en affichage inline, EPUB en pièce jointe.
- Status API expose les attestations de revue.
- Jeton distinct \`PAPI_KIDS_KDP_REVIEW_TOKEN\`, identité réviseur serveur, notes de 20 à 2000 caractères.
- Tests DB, API, téléchargements et migration.

## Limites
La revue ne change pas le package et ne publie rien. Le release gate devra exiger les attestations correspondant aux empreintes exactes des fichiers.
