# Mission 27 — Jour 5 : CI, sécurité et clôture

## Validation
- Migration additive appliquée sur PostgreSQL jetable et base locale PostgREST.
- Tests SQL couvrant producteur idempotent, conflit de contenu, claim, fencing, retry, dead-letter, lease expiré et audit.
- Test multi-session : exactement un worker obtient le même événement concurrent.
- Contrôle des privilèges anon/authenticated et accès service_role minimal au journal de tentatives.
- Test de rollback protégé.

## Limites résiduelles
- Aucun worker de livraison n'est activé.
- Aucune intégration prestataire n'est configurée.
- La garantie exactly-once externe est impossible sans coopération du destinataire.
- L'atomicité métier exige que mutation et enqueue soient dans la même transaction locale.
- Aucune base Supabase hébergée n'est touchée.
