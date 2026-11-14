# Mission 26 — Jour 5 : validation et clôture

## Contrôles
- Migration additive et test SQL sur PostgreSQL jetable.
- Exécution de la suite Python existante.
- Intégration PostgREST locale.
- Vérification des droits sur table et RPC.
- Vérification du rejet des portées erronées, expirations et rejeux.
- Vérification des événements d'émission et de consommation.

## Résultat attendu
La CI doit valider le SHA exact de la branche. La mission reste en attente si un job est en échec ou en cours.

## Limites résiduelles
- L'identité propriétaire est vérifiée par le backend, pas par la base.
- Aucun canal externe ni worker n'est connecté.
- Aucun effet externe n'est exécuté.
- L'idempotence d'une opération métier reste distincte de l'anti-rejeu d'approbation.
- Aucun environnement Supabase hébergé n'a été testé.
