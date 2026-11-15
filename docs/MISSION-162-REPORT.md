# Mission 162 — Revue humaine de sécurité persistée

## Livrable
- Migration PostgreSQL 017 : table append-only des revues de sécurité jeunesse, RLS activé, accès restreint au rôle serveur.
- Le callback de revue verrouille le livre, compare le SHA-256 courant au hash soumis et relit l'analyse de sécurité stockée par le worker.
- Décision, réviseur, date, référence de preuve, notes et compte d'alertes sont conservés dans une table d'audit et dans les métadonnées du livre.
- Approbation d'un manuscrit avec alertes : justification d'au moins 20 caractères obligatoire.
- Nouvel endpoint HTTPS avec jeton distinct \`PAPI_KIDS_SAFETY_REVIEW_TOKEN\`; identité du réviseur exclusivement côté serveur.
- Le status endpoint expose le rapport de sécurité et l'attestation, sans texte complet du manuscrit ni secrets.
- Le worker décode les octets UTF-8 sans normaliser CRLF afin que le hash de l'analyse corresponde exactement au SHA-256 de l'upload.

## Gouvernance
Une modification du manuscrit invalide l'ancienne revue. Les décisions restent append-only. Aucun appel IA, aucune dépense, aucun déploiement ou publication.
