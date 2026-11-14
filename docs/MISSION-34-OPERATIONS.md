# Mission 34 — Procédure opérateur

1. Exécuter `PYTHONPATH=runtime python -m papi_core supabase-preflight` pour contrôler le dépôt sans exiger de secrets.
2. Examiner la séquence, les empreintes et les rollbacks listés.
3. Configurer les variables uniquement dans l'environnement serveur protégé, jamais dans Git.
4. Exécuter `--require-configured` dans cet environnement pour contrôler la présence et la forme de la configuration.
5. Organiser séparément un test hébergé autorisé, avec projet dédié, secrets gérés, sauvegarde vérifiée, revue des privilèges et procédure d'arrêt.
6. Ne pas interpréter `ready_for_operator_review` comme une validation de disponibilité, d'authentification Supabase ou de production.

La commande n'applique jamais les migrations. Toute opération distante exige une mission et une autorisation distinctes.
