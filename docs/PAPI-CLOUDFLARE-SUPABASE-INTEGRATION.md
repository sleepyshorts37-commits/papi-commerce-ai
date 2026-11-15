# Mission 105 — Connexion Cloudflare au registre Supabase partagé

## Livrables
- `SupabaseNeuronQuotaLedger` dans `runtime/papi_core/image_provider_cloudflare.py`.
- Appels PostgREST vers les RPC de la migration 013 : réserve, commit, marquage incertain et libération.
- `CloudflareImageAdapter.from_shared_environment()` pour construire l'adaptateur avec le registre partagé.
- Tests unitaires simulant les réponses RPC ; aucune requête réelle n'est envoyée.
- Aucun changement du comportement de génération par défaut : le ledger mémoire reste utilisable pour les tests isolés.

## Configuration serveur
Variables nécessaires :
- `SUPABASE_URL` : URL HTTPS du projet.
- `SUPABASE_SERVICE_ROLE_KEY` : secret serveur, uniquement dans le gestionnaire de secrets backend.
- `CLOUDFLARE_ACCOUNT_ID` : identifiant de compte, utilisé comme référence de compartiment.
- `CLOUDFLARE_API_TOKEN` : jeton serveur Cloudflare, jamais exposé au client.
- `PAPI_WORKER_ID` : identifiant du worker (défaut `PAPI-IMAGE-01`).
- `PAPI_CLOUDFLARE_DAILY_NEURON_LIMIT` : plafond confirmé (défaut technique 10 000, à ne pas considérer comme droit contractuel du compte).

Exemple d'initialisation dans un backend autorisé :

```python
from papi_core.image_provider_cloudflare import CloudflareImageAdapter

adapter = CloudflareImageAdapter.from_shared_environment(
    model_costs={"@cf/your-approved-model": 100},
    free_tier_confirmed_for_account=True,  # seulement après vérification du compte
)
```

Le coût par modèle doit être vérifié et configuré avant l'activation. Le plafond doit correspondre à la limite confirmée pour le compte et ne doit pas être augmenté sur la seule base du défaut logiciel.

## Séquence
1. Le worker demande une réservation Supabase avec clé d'idempotence, modèle, estimation et date UTC.
2. PostgreSQL verrouille la clé et le compartiment ; une réservation concurrente excédentaire est rejetée.
3. Cloudflare est appelé uniquement après confirmation de la réservation.
4. Après réponse image, le backend commit la consommation estimée.
5. Timeout, réponse non concluante ou échec de commit : le backend marque la réservation incertaine lorsque possible et conserve le quota jusqu'au rapprochement.

## Sécurité et limites
- La clé service-role n'est utilisée que dans le backend ; ne jamais l'utiliser dans un navigateur, une app mobile ou un agent côté client.
- Aucun secret ni identifiant réel n'a été ajouté au dépôt.
- Le code n'applique pas la migration et n'appelle aucun compte Cloudflare/Supabase réel.
- Le registre partagé fonctionne uniquement après application préalable de la migration 013 sur la base ciblée.
- Les unités restent des estimations configurées ; aucun endpoint d'usage réel Cloudflare n'est interrogé ici.
- Le résultat image n'est pas persisté par cette couche ; réutiliser la même clé après commit bloque une nouvelle génération mais ne restitue pas l'image précédente.

## Validation restante
- Exécuter les tests Python dans l'environnement du dépôt.
- Appliquer migration 013 et tests SQL sur PostgreSQL local isolé.
- Ajouter un test multi-session PostgreSQL pour prouver l'absence de dépassement concurrent.
- Configurer les secrets uniquement dans un environnement de test autorisé avant tout essai d'intégration.
