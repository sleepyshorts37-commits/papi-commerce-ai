# Mission 118 — Sécurisation des rejeux du registre partagé de quotas

## Objectif
Finaliser la jonction entre l'adaptateur Python Cloudflare Workers AI et le registre transactionnel Supabase/PostgreSQL, en empêchant qu'une réservation existante soit interprétée comme une autorisation de soumettre une seconde fois la même génération.

## Constat initial
- La migration 013, l'adaptateur `SupabaseNeuronQuotaLedger`, le constructeur `CloudflareImageAdapter.from_shared_environment()` et les tests multi-session existaient déjà.
- Le RPC de réservation renvoyait le statut `reserved` aussi bien pour une nouvelle réservation que pour le rejeu idempotent d'une réservation encore ouverte.
- L'adaptateur ne pouvait donc pas distinguer la première autorisation de soumission d'un rejeu après redémarrage. Cela créait un risque de double appel fournisseur.

## Modifications
- Le RPC `papi_reserve_provider_quota` renvoie désormais `reused_reserved` lorsqu'une clé existante pointe vers une réservation encore `reserved`.
- L'adaptateur n'autorise l'appel Cloudflare que pour le statut exact `reserved`; un rejeu est donc bloqué avant tout trafic fournisseur.
- Le contrat SQL vérifie explicitement le statut de rejeu.
- Les tests Python couvrent le statut `reused_reserved`, les transitions `uncertain` et `released`, ainsi que l'absence d'appel Cloudflare pour un rejeu.
- Le script PostgreSQL ajoute un scénario de 12 sessions concurrentes utilisant la même clé : une création, onze rejeux, une seule réservation et une seule consommation réservée.
- La documentation décrit le contrat et les scénarios.

## Sécurité et limites
- Aucun appel vers un projet Supabase hébergé ou un compte Cloudflare réel.
- Aucun secret ajouté au dépôt.
- Aucun worker permanent, achat, service payant ou déploiement.
- Les tests PostgreSQL exigent uniquement un PostgreSQL local isolé et le client `psql`.
- Le plafond et le coût par modèle restent à confirmer depuis les informations officielles du compte avant toute activation réelle.
- Une réservation existante encore ouverte est bloquée au rejeu et nécessite une réconciliation si son état réel est inconnu.

## Plan de travail (5 jours)
1. Revue du contrat SQL, des privilèges et de la sémantique d'idempotence.
2. Correction du statut de rejeu et garde-fou avant soumission Cloudflare.
3. Tests unitaires Python et tests SQL de contrat.
4. Test multi-session PostgreSQL : rejeu de clé identique et vagues 10/20/50 workers.
5. Revue de sécurité, documentation, CI et rapport de clôture.

## État de validation
- Modifications poussées sur une branche dédiée.
- CI GitHub à attendre : la mission n'est pas déclarée terminée avant succès des tests Python et PostgreSQL.
- Aucun merge vers `main`.
