# Persistance partagée — Supabase

## Ce qui est prêt dans le dépôt
- Adaptateur Python PostgREST dans `runtime/papi_core/storage.py`.
- Tables PostgreSQL pour les missions et le journal d'audit dans `infra/supabase/schema.sql`.
- Contrôle optimiste de version pour empêcher les écrasements concurrents.
- Fonction RPC `papi_commit_task_change` : mise à jour de la mission et insertion de l'événement d'audit dans une seule transaction PostgreSQL.
- Méthodes `transition_and_save` et `approve_and_save` qui appliquent la machine à états avant l'appel transactionnel.
- Tests unitaires avec appels réseau simulés ; aucune connexion réelle n'est utilisée par les tests.

## Mise en service (pas encore effectuée)
1. Créer un projet Supabase gratuit si ses limites et conditions conviennent.
2. Ouvrir le SQL Editor et exécuter intégralement `infra/supabase/schema.sql`.
3. Dans un environnement serveur protégé, définir `SUPABASE_URL` et `SUPABASE_KEY`.
4. Utiliser une clé serveur/service role uniquement côté serveur. Ne jamais la placer dans le code du navigateur, un dépôt public, une issue ou un message.
5. Tester les accès, les droits, les sauvegardes et la restauration avant d'y mettre des données réelles.

## Exemple d'utilisation
```python
from papi_core.storage import SupabaseStore

store = SupabaseStore()
updated_task, new_version = store.transition_and_save(
    "PAPI-001",
    "ready",
    actor="marietou",
    expected_version=1,
    reason="Mission validée pour préparation",
)
```

Pour une mission nécessitant l'accord du propriétaire, utiliser `approve_and_save` avec l'identité de l'approbateur et la décision explicite. L'approbation ne lance pas la mission ; la transition ultérieure vers `in_progress` reste soumise aux règles de la machine à états.

## Sécurité et limites
- Aucune clé Supabase n'est présente dans ce dépôt.
- Les tables et la fonction RPC refusent les accès directs des rôles `anon` et `authenticated`. Le backend utilise une clé serveur protégée.
- La fonction SQL est `SECURITY INVOKER` : elle s'exécute avec les droits de l'appelant ; seul `service_role` reçoit le droit d'exécution.
- Une erreur de version ou d'insertion d'audit annule toute la transaction PostgreSQL.
- L'adaptateur ne déclenche aucune prospection, publication ou transaction financière.
- Aucun projet Supabase n'a été créé ou connecté depuis ce dépôt. Cette persistance n'est donc pas encore opérationnelle.
- Les agents restent des rôles documentés ; aucune autonomie permanente n'est activée.
