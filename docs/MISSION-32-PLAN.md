# Mission 32 — PAPI MULTI-INSTANCE MEMORY & CHAT SYNC

## Objectif
Synchroniser explicitement mémoire partagée et messagerie interne entre instances, en s'appuyant sur les tables append-only existantes (migrations 004/005) et sans modifier l'autonomie des agents.

## Livrables prévus sur cinq jours
1. Audit des contrats locaux, des identités et des tables partagées.
2. Adaptateurs Supabase injectables pour publier et lire mémoire/chat.
3. Pagination keyset, idempotence et contrôles de visibilité par agent/destinataire.
4. Migration additive 016 pour lecture mémoire filtrée en base, tests unitaires/SQL et CI.
5. Documentation de configuration, sécurité, reprise et limitations.

## Sécurité
- Local par défaut ; distant seulement par injection explicite d'un store serveur.
- Service role uniquement dans un backend fiable ; il ne constitue pas une identité d'agent. Les acteurs doivent être validés par la frontière d'authentification.
- Mémoire agent isolée ; les événements supersede ne sont visibles que si leur mémoire cible l'est ; messages directs filtrés ; diffusion all limitée aux agents habilités.
- Aucun secret, donnée client ou journal réel dans le dépôt.
- Aucun déploiement, connexion distante, message externe, dépense ou activation autonome.

## Critères
Adaptateurs testés, idempotence, pagination sans doublon, isolation, CI verte sur SHA exact, documentation claire, PR draft ouverte non fusionnée.
