# Mission 32 — PAPI MULTI-INSTANCE MEMORY & CHAT SYNC

## Objectif
Synchroniser explicitement mémoire partagée et messagerie interne entre instances, en s'appuyant sur les tables append-only existantes (migrations 004/005) et sans modifier l'autonomie des agents.

## Livrables prévus sur cinq jours
1. Audit des contrats locaux, des identités et des tables partagées.
2. Adaptateurs Supabase injectables pour publier et lire mémoire/chat.
3. Pagination keyset, idempotence et contrôles de visibilité par agent/destinataire.
4. Tests unitaires simulés, tests SQL/CI si changement SQL requis.
5. Documentation de configuration, sécurité, reprise et limitations.

## Sécurité
- Local par défaut ; distant seulement par injection explicite d'un store serveur.
- Service role uniquement dans un backend fiable ; il ne constitue pas une identité d'agent. Les acteurs doivent être validés par la frontière d'authentification.
- Mémoire agent isolée ; messages directs filtrés ; diffusion all limitée aux agents autorisés.
- Aucun secret, donnée client ou journal réel dans le dépôt.
- Aucun déploiement, connexion distante, message externe, dépense ou activation autonome.

## Critères
Adaptateurs testés, idempotence, pagination sans doublon, isolation, CI verte sur SHA exact, PR draft ouverte non fusionnée.
