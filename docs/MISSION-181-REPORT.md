# Mission 181 — Intégrité de l'audit KDP et couverture CI

## Constat initial
La PR Mission 180 possédait un workflow PAPI core vert, mais le workflow ne rejouait que les migrations PAPI KIDS 013–016. Les migrations 017–023 et leurs contrats SQL existaient dans la branche sans être appliqués dans les deux jobs PostgreSQL de CI. Le succès CI ne constituait donc pas une preuve d'intégration de la chaîne KDP récente.

## Changements
- Migration 024 : verrou append-only sur les événements de cycle de soumission KDP ; toute mise à jour, suppression ou troncature échoue avec le code SQLSTATE 55000.
- La relation vers le livre passe de ON DELETE CASCADE à ON DELETE RESTRICT afin qu'une suppression du livre ne puisse pas effacer les preuves de soumission.
- Les privilèges UPDATE, DELETE et TRUNCATE sont explicitement retirés à service_role.
- Test SQL transactionnel : vérifie le trigger, la règle FK, le rejet d'UPDATE/DELETE/TRUNCATE et la conservation du livre et de l'événement.
- Les deux jobs PostgreSQL de CI appliquent désormais les migrations 017–024 et exécutent les tests SQL correspondants.
- Le diagnostic readiness exige la présence des deux triggers d'immutabilité.
- Documentation d'exploitation et roadmap mises à jour.

## Limites et gouvernance
- Tests uniquement sur des bases PostgreSQL jetables de CI ; aucune migration n'a été appliquée à un projet Supabase distant.
- Aucun secret, compte externe, publication KDP, agent, worker permanent ou dépense n'a été activé.
- La chaîne de soumission reste manuelle ; la déclaration de mise en ligne demeure une attestation du propriétaire, pas une vérification Amazon indépendante.
