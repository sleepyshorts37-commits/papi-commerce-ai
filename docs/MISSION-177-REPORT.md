# Mission 177 — Attestation Kindle Previewer persistée

## Livrable
- Migration PostgreSQL 021 : journal append-only des contrôles Kindle Previewer, RLS, version package, hash EPUB, décision, réviseur, date, preuve et notes.
- Endpoint HTTPS avec jeton distinct \`PAPI_KIDS_KINDLE_PREVIEWER_TOKEN\`.
- Vérifie que le SHA-256 soumis correspond à l'EPUB du dernier package.
- Le tableau de bord iPhone permet d'enregistrer la réussite ou l'échec, avec SHA-256 de preuve et notes.
- Le status API expose l'attestation.
- Le release gate exige une preuve SHA-256, notes, identité et version correspondante ; un nouvel EPUB invalide la revue précédente.

## Gouvernance
L'attestation est manuelle : le service ne prétend pas exécuter Kindle Previewer. Aucun upload KDP ou publication.
