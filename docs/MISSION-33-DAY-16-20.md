# Mission 33 — Jours 16 à 20 : validation opérationnelle et transfert

16. Environnement de test isolé : PostgreSQL 16 et PostgREST local jetables, données fictives, exécutés dans GitHub Actions ; aucun projet Supabase distant n'est utilisé.
17. Matrice automatisée : contrat de visibilité, réconciliation, intégrité du plan, approbation signée, mauvais digest/destination/action set, nonce rejoué, consommation SQL exacte, rejeu SQL et privilèges.
18. Contrat d'observabilité sans contenu défini : correlation ID, digest, action ID, instance, type, latence et code d'erreur catégorisé. Les contenus mémoire/chat et secrets sont exclus.
19. Runbook documenté : sauvegarde, restauration, arrêt d'urgence, rotation des clés, rollback prudent et escalade humaine.
20. Revue finale, CI sur le SHA exact et transfert via PR draft.

## Résultat et limites
- Les environnements jetables CI et les contrats SQL locaux sont exécutés par le workflow ; ils ne prouvent pas la disponibilité d'un projet Supabase distant.
- Les tests multi-instances réels sur deux projets Supabase, la sauvegarde/restauration distante et la revue indépendante externe ne sont pas exécutables sans projet, identifiants et autorisation du propriétaire.
- Aucun transfert, aucune migration distante, aucun déploiement ni activation de worker n'a été réalisé.
