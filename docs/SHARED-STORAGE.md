# Persistance partagée — Supabase

## Ce qui est prêt
- Adaptateur Python PostgREST dans `runtime/papi_core/storage.py`.
- Tables PostgreSQL pour les missions et le journal d'audit dans `infra/supabase/schema.sql`.
- Contrôle optimiste de version : une mise à jour ne réussit que si la version lue est toujours actuelle.
- Identifiant unique sur les événements d'audit pour éviter les doublons.
- Tests unitaires avec appels réseau simulés.

## Mise en service (pas encore effectuée)
1. Créer un projet Supabase gratuit si ses limites et conditions conviennent.
2. Ouvrir le SQL Editor et exécuter `infra/supabase/schema.sql`.
3. Dans un environnement serveur protégé, définir `SUPABASE_URL` et `SUPABASE_KEY`.
4. Utiliser une clé serveur/service role uniquement côté serveur. Ne jamais la placer dans le code du navigateur, un dépôt public, une issue ou un message.
5. Tester les accès, les droits, les sauvegardes et la restauration avant d'y mettre des données réelles.

## Exemple
```python
from papi_core.storage import SupabaseStore

store = SupabaseStore()
version = store.save_task({"id": "PAPI-001", "status": "backlog"})
current = store.get_task("PAPI-001")
updated_version = store.save_task(
    {"id": "PAPI-001", "status": "ready"},
    expected_version=current["version"],
)
```

## Sécurité et limites
- Aucune clé Supabase n'est présente dans ce dépôt.
- Les tables refusent les accès directs des rôles `anon` et `authenticated`. Le backend utilise une clé serveur protégée.
- L'adaptateur ne déclenche aucune transition, prospection, publication ou transaction.
- La sauvegarde de la tâche et l'ajout de son événement d'audit ne sont pas encore atomiques ensemble : prévoir une fonction SQL transactionnelle/RPC avant un usage multi-agent critique.
- Aucun projet Supabase n'a été créé ou connecté depuis ce dépôt. Le stockage partagé ne devient opérationnel qu'après configuration et tests dans le projet choisi.
