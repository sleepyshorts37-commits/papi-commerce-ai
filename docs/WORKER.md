# Worker contrôlé

## Fonctionnement
`PapiWorker.run_once()` traite au maximum un job :
1. Vérifie le mode d'exécution avant toute réservation.
2. Réserve un job avec le bail exclusif existant.
3. Charge la tâche associée dans Supabase.
4. Passe par le registre de handlers et la politique de permissions.
5. Exécute le handler enregistré puis confirme le résultat avec le bail.
6. En cas de blocage ou d'erreur, signale un code d'erreur générique à la file.

## Protection
- Si `execution_enabled` est faux, le worker ne réserve aucun job.
- Aucun handler n'est chargé depuis le payload.
- Aucun job n'est exécuté si la tâche ou ses permissions ne sont pas valides.
- Les messages d'erreur détaillés et les secrets ne sont pas renvoyés dans le statut du worker.
- Un résultat n'est marqué terminé que si Supabase confirme la réservation du bail.

## Utilisation locale (après configuration)
Le worker est appelé explicitement une fois par le processus qui l'héberge. Il ne crée ni boucle infinie, ni planificateur, ni service permanent. Le registre doit être construit par le code de confiance et la politique chargée depuis un fichier protégé.

## État de déploiement
Ce composant est un worker à exécution unique, pas un service 24/7. Aucun projet Supabase n'est connecté, aucune clé n'est fournie et aucun worker n'est déployé. La politique du dépôt garde l'exécution désactivée.
