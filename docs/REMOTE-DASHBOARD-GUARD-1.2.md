# Garde de démarrage du tableau de bord distant 1.2

La commande `dashboard-remote` commence désormais par appeler `SupabaseStore.check_readiness()`.

Ordre de traitement :
1. Vérifier la configuration locale et construire le client Supabase.
2. Effectuer les deux sondes GET limitées sur `papi_tasks` et `papi_audit_events`.
3. Si le contrôle n'est pas `ready`, afficher un diagnostic générique, retourner le code 2 et **ne pas charger** les tâches ni l'historique.
4. Si le contrôle est `ready`, charger le tableau de bord distant et joindre le résultat du précontrôle.

Le précontrôle ne constitue pas une garantie que les lectures ultérieures réussiront : les droits, la disponibilité ou les données peuvent changer entre les requêtes. Les erreurs de lecture restent traitées par le mécanisme d'erreur du stockage.

Toutes les opérations de ce parcours sont en lecture seule (GET). Aucun agent ou worker n'est démarré. Aucun message, achat, paiement, transfert ou autre action externe n'est déclenché.

Les tests automatisent les deux chemins à l'aide de doubles de test. Ils ne prouvent pas qu'un projet Supabase réel est configuré ou accessible.
