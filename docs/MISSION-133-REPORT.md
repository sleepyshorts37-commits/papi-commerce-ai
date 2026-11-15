# Mission 133 — File éditoriale persistante et analyse structurelle hors ligne

## Livrables
- Le dépôt authentifié crée désormais un travail éditorial `job.json` dans le même répertoire privé que le manuscrit et ses métadonnées.
- Le statut initial devient `queued_for_analysis`.
- L'identifiant `PKP-UP-<sha256-prefix>` est déterministe : un contenu identique retourne la référence existante (HTTP 200) au lieu de créer un doublon. Le premier dépôt retourne HTTP 201.
- La création se fait dans un répertoire temporaire privé puis par renommage atomique vers le répertoire final ; fichiers en mode 0600, répertoire en mode 0700.
- Nouveau module `papi_kids_editorial_queue.py` : lecture contrôlée de la file et analyse déterministe locale des titres Markdown. Le worker met à jour les statuts vers `analysis_ready` ou `needs_editor_review`.
- L'analyse n'appelle aucun LLM, aucune API image et aucun fournisseur. Elle ne publie rien et conserve la validation éditoriale humaine obligatoire.
- Tests couvrent l'idempotence, le stockage de la file, l'analyse hors ligne, le cas sans titres et les références invalides.

## Décision d'architecture et limites
- Le projet Supabase accessible `papi-commerce-ai` est actif, mais l'inspection a retourné zéro table publique et zéro migration. Aucune migration n'a été appliquée à la base active.
- Pour ne pas inventer un schéma ni modifier la base de production sans validation, cette mission utilise une file JSON privée sur le volume de stockage configuré. L'hébergeur doit fournir un volume persistant, privé, sauvegardé et partagé si plusieurs workers sont utilisés.
- Ce mécanisme n'est pas une file distribuée transactionnelle multi-instance. Une prochaine étape devra ajouter un backend PostgreSQL/Supabase avec tables, contraintes d'unicité, RLS et prise de tâche atomique avant d'activer plusieurs workers.
- Le worker d'analyse est une fonction interne explicite ; l'upload ne le déclenche pas automatiquement. Son invocation et toute analyse IA future devront avoir une autorisation distincte.

## Variables et exploitation
- Conserver `PAPI_KIDS_UPLOAD_TOKEN` et `PAPI_KIDS_PRIVATE_STORAGE_DIR` uniquement dans les secrets et la configuration serveur.
- Monter le dossier privé sur un volume persistant ; ne jamais l'exposer comme contenu statique/public.
- Lancer `analyze_queued_manuscript(storage_root, upload_id)` depuis un worker serveur contrôlé après validation de la politique d'exploitation.
- Aucun secret ajouté au dépôt ; aucun appel externe, coût, achat de crédits, déploiement ou publication effectué.

## Validation
- Tests unitaires hors réseau ajoutés ; CI GitHub doit confirmer le résultat après ouverture de la PR.
- Aucun changement n'a été appliqué au projet Supabase actif.
