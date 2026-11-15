# Mission 110 — Débit de génération d'images et gouvernance des quotas

## Objectif
Accélérer la génération d'images PAPI en permettant des lots de requêtes parallèles bornées, sans contourner les quotas fournisseur. Corriger également le défaut découvert dans la CI de la mission 109.

## Découverte CI
Les workflows GitHub associés au commit de la mission 109 ont révélé 11 erreurs dans les tests de l'adaptateur Cloudflare. Le validateur de modèle refusait les identifiants Cloudflare standards commençant par `@cf/`. Le même validateur empêchait le registre Supabase de réserver un modèle tel que `@cf/test/image`. Les tests unitaires échouaient avant les appels réseau ; le job SQL concurrent était donc ignoré. Le workflow PostgREST local distinct a réussi.

## Réalisations
1. Ajout de `MODEL_IDENTIFIER`, distinct de la validation des identifiants de compte, pour accepter les identifiants fournisseur préfixés par `@`.
2. Correction de la validation des modèles dans l'adaptateur et le registre Supabase.
3. Ajout de `generate_many` : génération parallèle, ordre de sortie préservé, résultat indépendant par image, lot plafonné à 500.
4. Concurrence réglable entre 1 et 16 workers, valeur par défaut 4.
5. Validation des champs requis et rejet des clés d'idempotence dupliquées avant tout appel réseau.
6. Chaque image conserve sa réservation transactionnelle : le parallélisme ne permet pas de dépasser les quotas.
7. Ajout de tests de lots, d'idempotence et de limite de concurrence.
8. Mise à jour du filtre de chemins GitHub Actions pour déclencher le workflow quota lors des changements de l'adaptateur et de ses tests.
9. Documentation de l'API de génération par lots et de son exploitation.

## Fichiers modifiés
- `runtime/papi_core/image_provider_cloudflare.py`
- `tests/test_image_provider_cloudflare.py`
- `.github/workflows/papi-shared-quota-postgres.yml`
- `docs/PAPI-IMAGE-BATCH-THROUGHPUT.md`
- `docs/MISSION-110-REPORT.md`

## Vérification
- Les logs GitHub Actions de la mission 109 ont été lus ; le défaut du préfixe `@cf/` est identifié.
- Les tests ont été ajoutés mais ne sont pas encore exécutés sur le nouveau commit au moment de la rédaction.
- Aucun appel Cloudflare réel, aucun projet Supabase hébergé et aucun secret n'ont été utilisés.
- Aucun quota gratuit réel n'est présumé : le statut gratuit du compte doit rester explicitement confirmé.
- La concurrence augmente le débit potentiel mais ne garantit ni le temps de réponse fournisseur ni un nombre d'images/jour.

## Gouvernance et limites
- Aucune génération n'est lancée automatiquement par ce code ; l'appel explicite à `generate_many` reste requis.
- Aucun fallback payant, retry automatique ou relâchement automatique d'une réservation incertaine.
- Le journal append-only et la correction à double approbation restent à concevoir dans une migration Supabase générée avec le CLI conforme ; aucune migration SQL n'est fabriquée manuellement.
- PR brouillon uniquement, non fusionnée.

## Prochaine étape
Après validation CI, connecter le planificateur de lots à la chaîne PAPI Image Factory : priorisation des pages, répartition par modèle selon coût confirmé, stockage des résultats, contrôle qualité, puis assemblage des livres. Mesurer les images réussies par heure et par quota consommé avant d'augmenter la concurrence.
