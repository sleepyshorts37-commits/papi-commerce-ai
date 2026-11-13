# Worker contrôlé

## Fonctionnement
`PapiWorker.run_once()` traite au maximum un job :
1. Vérifie le mode d'exécution avant toute réservation.
2. Réserve un job avec le bail exclusif existant.
3. Charge la tâche associée dans Supabase.
4. Valide localement le type et la cohérence des champs d'approbation avant toute authentification d'agent.
5. Résout le handler, authentifie cryptographiquement l'identité de l'agent, puis applique la politique complète avec attribution au principal authentifié.
6. Renouvelle le bail avant le handler, journalise `job.handler_started` de façon fail-closed, exécute le handler enregistré puis confirme le résultat avec le bail.
7. En cas de blocage ou d'erreur, signale un code d'erreur générique à la file et journalise les transitions selon les garanties du worker.

## Protection
- Si `execution_enabled` est faux, le worker ne réserve aucun job.
- Aucun handler n'est chargé depuis le payload.
- `approval_required` doit être un booléen strict ; les statuts autorisés sont `not_required`, `pending`, `approved` et `rejected`, avec cohérence entre les champs.
- Une approbation requise doit être explicitement `approved` avant toute authentification d'agent ou exécution.
- Les refus de politique après authentification sont attribués au principal authentifié ; les échecs d'authentification restent attribués au worker système.
- Aucun handler ne démarre sans bail renouvelé et événement `job.handler_started` durable.
- Aucun job n'est exécuté si la tâche ou ses permissions ne sont pas valides.
- Les messages d'erreur détaillés et les secrets ne sont pas renvoyés dans le statut du worker.
- Un résultat n'est marqué terminé que si Supabase confirme la réservation du bail.

## Utilisation locale (après configuration)
Le worker est appelé explicitement une fois par le processus qui l'héberge. Il ne crée ni boucle infinie, ni planificateur, ni service permanent. Le registre doit être construit par le code de confiance et la politique chargée depuis un fichier protégé.

## État de déploiement
Ce composant est un worker à exécution unique, pas un service 24/7. Aucun projet Supabase n'est connecté, aucune clé n'est fournie et aucun worker n'est déployé. La politique du dépôt garde l'exécution désactivée.
