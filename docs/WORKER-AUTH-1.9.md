# PAPI WORKER AUTHENTICATION & SECURITY 1.9

## Contrat
`runtime/papi_core/worker_auth.py` authentifie les opérations worker à l'aide du mécanisme d'identité agent Ed25519 existant. Chaque enveloppe signe exactement les champs `operation`, `worker_id`, `job_id` et `lease_token`.

- `worker_id` doit être strictement égal à `agent_id` du signataire.
- Opérations permises : `claim`, `heartbeat`, `complete`, `fail`.
- Chaque opération exige sa permission dédiée sur la carte active : `worker.claim_jobs`, `worker.heartbeat`, `worker.complete`, `worker.fail`.
- Le claim exige `job_id: null`, car le job n'est pas encore attribué.
- Les autres opérations exigent un identifiant de job et un lease token UUID.
- L'authentification déléguée vérifie la carte active/complète, la cohérence du registre, la signature Ed25519, la fraîcheur, la version de clé et le nonce anti-rejeu.

## Limites de sécurité
Ce module valide une preuve signée ; il ne remplace pas les contrôles atomiques de la base de données. Le lease token doit encore être comparé par les RPC Supabase à la réservation courante. L'appelant doit invoquer l'authentification avant chaque opération et ne doit jamais exposer les RPC à un worker non authentifié. Le nonce signé ne remplace pas l'idempotence métier.

Aucun worker n'est lancé. Aucun handler n'est exécuté. Aucune carte agent n'est activée. La politique reste désactivée (budget nul, exécution et actions externes désactivées). Les clés privées ne sont pas stockées dans GitHub.
