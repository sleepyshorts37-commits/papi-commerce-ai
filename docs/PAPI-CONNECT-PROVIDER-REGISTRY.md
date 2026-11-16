# Mission 183 — PAPI CONNECT PROVIDER REGISTRY

## Livrables
- `schemas/provider-registry.schema.json` : contrat JSON Schema Draft 2020-12.
- `data/providers.json` : catalogue versionné des fournisseurs candidats.
- `runtime/papi_core/provider_registry.py` : validation stricte, lecture locale, recherche et contrôle d'autorisation.
- `tests/test_provider_registry.py` : tests locaux sans réseau.

## Règles
- Le registre est une source de configuration, jamais un coffre à secrets.
- `credentials_env` contient uniquement des noms de variables d'environnement, jamais leurs valeurs.
- Tous les fournisseurs commencent avec `status=proposed` et `enabled=false`.
- `unknown` signifie que le prix et les quotas ne sont pas vérifiés : ne pas présenter le service comme gratuit.
- Le plafond local par défaut est de 0 XOF. Aucun coût n'est autorisé par défaut.
- Un fournisseur vérifié ou activé doit avoir une date de vérification récente.
- L'accès exige toutes les permissions déclarées par l'agent. Les fournisseurs externes exigent une approbation explicite du propriétaire.
- Cette mission ne crée aucun compte, secret, abonnement, déploiement ou appel réseau.

## Fournisseurs catalogués
Gemini API, Ollama/llama.cpp, n8n, Langfuse, Supabase et MCP Python SDK. Leur présence signifie uniquement « candidat documenté » ; aucune disponibilité gratuite ou régionale n'est garantie.

## Vérification
`PYTHONPATH=runtime python -m unittest discover -s tests -v`
Les tests seront exécutés par GitHub Actions : aucun ordinateur local n'est nécessaire.
