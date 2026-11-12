# Supabase — mémoire historique des agents 0.8

## Lecture du journal distant
\`SupabaseStore.get_audit_events(limit=500, offset=0)\` lit une page du journal \`papi_audit_events\` avec un tri déterministe sur \`occurred_at\` puis \`event_id\`. Les paramètres sont bornés (1 à 1000 lignes par page, offset positif). Chaque ligne est validée par le schéma commun du journal d'audit.

\`SupabaseStore.get_agent_history(agent_id, tasks, page_size=500, max_pages=20, as_of=None)\` lit les pages nécessaires puis délègue le calcul au module historique 0.6. Le parcours est limité à 20 000 événements. Si toutes les pages autorisées sont pleines, la méthode refuse de présenter un résultat potentiellement tronqué comme complet.

## Sécurité
- Requêtes GET uniquement dans ces deux nouvelles méthodes.
- Aucun ajout, modification ou suppression d'événement.
- La clé serveur reste dans l'environnement protégé et n'est jamais affichée.
- Les permissions SQL existantes gardent les tables hors d'accès des rôles anon et authenticated ; seul le backend de confiance utilise service_role.
- Les tâches sont fournies explicitement à la méthode : cette version ne lit pas automatiquement toutes les tâches depuis Supabase.
- Aucune connexion Supabase réelle n'est effectuée pendant les tests unitaires.

## Mise en service
Le projet Supabase doit être créé et le schéma SQL appliqué par le propriétaire. Définir ensuite SUPABASE_URL et SUPABASE_KEY dans un environnement serveur protégé. La présence des variables ne prouve pas que les droits ni le réseau sont valides. Aucun identifiant de connexion ne doit être ajouté au dépôt public.
