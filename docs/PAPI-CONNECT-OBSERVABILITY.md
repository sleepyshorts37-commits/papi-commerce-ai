# Mission 186 — Observabilité locale PAPI CONNECT

## Objectif

Mesurer les appels qui traversent la passerelle sans connecter de fournisseur réel, sans transmettre de données et sans engager de dépense. Cette mission remplace provisoirement le raccordement d'un fournisseur réel initialement envisagé pour Mission 186 : les conditions, quotas, régions, droits commerciaux et autorisations humaines ne sont pas encore réunis.

## Livrables

- `runtime/papi_core/connect_observability.py` : journal JSONL local et rapport agrégé en lecture seule.
- `ConnectorTelemetry` : écrit des événements `started`, `completed` et `failed` en réutilisant le journal d'audit existant.
- `build_connector_usage_report` : vérifie la cohérence des événements et calcule les appels, échecs, opérations incomplètes, durées et coûts indicatifs.
- `papi connect-report` : affiche le rapport local sans créer de fichier ni effectuer de connexion.
- Tests dédiés sans réseau ni fournisseur externe.

## Données conservées

Le journal conserve uniquement :
- identifiant de fournisseur et type `text` / `image` ;
- identifiant d'opération aléatoire ;
- estimation XOF fournie à la requête ;
- durée en millisecondes ;
- coût déclaré par l'adaptateur, indicateur de simulation ou code d'erreur normalisé.

Il ne conserve jamais :
- prompt, réponse, image, empreinte de contenu ou identifiant de projet ;
- nom de client, donnée personnelle, credential, secret ou diagnostic brut d'un SDK.

Les tentatives bloquées avant l'exécution de l'adaptateur ne sont pas comptabilisées par ce journal. Les événements de début sans événement terminal restent visibles comme opérations incomplètes.

## Fiabilité et limites

- Le journal est local, append-only via l'API d'audit existante et limité à 5 MiB.
- Le modèle d'écriture est mono-écrivain ; il ne s'agit pas d'une base partagée multi-processus.
- Si l'événement de début ne peut pas être écrit, l'appel adaptateur est bloqué.
- Si l'événement terminal ne peut pas être écrit après l'appel, le résultat n'est pas remis à l'appelant ; le rapport conserve l'opération comme incomplète et une réconciliation est requise avant tout nouvel essai.
- Aucun retry automatique n'est ajouté.
- Les montants sont des estimations ou déclarations d'adaptateur, pas des factures, paiements ou écritures comptables vérifiés.
- `simulated=false` signifie uniquement que l'adaptateur n'a pas marqué le résultat comme simulé ; cela ne prouve pas qu'il s'agit d'un fournisseur distant.
- Aucun export vers Langfuse, Supabase, Google ou autre service n'est réalisé.

## Commandes

```sh
PYTHONPATH=runtime python -m papi_core connect-report
PYTHONPATH=runtime python -m papi_core connect-report --ledger-path /chemin/vers/connectors.jsonl
PYTHONPATH=runtime python -m unittest tests.test_connect_observability -v
```

Le rapport lit `data/telemetry/connectors.jsonl` par défaut. Si le fichier n'existe pas, il renvoie des compteurs à zéro sans le créer.

## Vérification

Vérification CI sur le SHA `686704ec48ca91b164a570fb2d8b913045787c1b` : PAPI core tests **250 tests réussis** (run [#44266657500](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/44266657500)), registry validation **succès** (run [#44266657368](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/44266657368)) et documentation checks **succès** (run [#44266657347](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/44266657347)). Le schéma Supabase a été appliqué à PostgreSQL jetable ; Supabase Preview a été ignoré. Aucun test d'intégration fournisseur, appel réseau ou contrôle de facturation réelle n'est revendiqué.
