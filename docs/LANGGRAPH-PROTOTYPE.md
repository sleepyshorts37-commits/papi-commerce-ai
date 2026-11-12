# Prototype LangGraph — démonstration en lecture seule

## Objectif

Tester l'intégration de LangGraph sans remplacer le noyau PAPI, sans modèle IA,
sans accès réseau et sans déclencher le worker. Le prototype est isolé dans
`papi_core.langgraph_demo`.

## Contrat

- Le graphe reçoit une fonction `preview(request)` explicitement injectée.
- Cette fonction doit être locale, déterministe et strictement en lecture seule.
- Le graphe valide la demande (texte non vide, 500 caractères maximum).
- Les sorties non conformes et exceptions sont converties en codes génériques ;
  aucun message d'exception n'est exposé.
- L'historique de démonstration est borné aux dix dernières demandes.
- Aucun checkpointer n'est activé par défaut. La mémoire n'existe que si un
  checkpointer est explicitement fourni par l'appelant.
- Le prototype ne crée aucun agent autonome, ne lit aucune donnée client et
  n'appelle ni Supabase, ni API, ni outil externe.

## Installation facultative

Dans un environnement de développement isolé, installer LangGraph selon sa
documentation officielle et les règles de dépendances du projet. Cette
installation n'est pas requise pour utiliser le noyau PAPI. Aucun fournisseur
de modèle n'est configuré et aucun appel payant n'est effectué par ce prototype.

## Exemple local

```python
from papi_core.langgraph_demo import build_readonly_demo_graph

def preview(request: str) -> dict:
    # Remplacer uniquement par une fonction locale en lecture seule.
    return {"request": request, "mode": "preview"}

graph = build_readonly_demo_graph(preview)
result = graph.invoke({"request": "vérifier le statut du prototype"})
print(result["status"])
```

Pour tester la mémoire/reprise, injecter explicitement un checkpointer LangGraph
et réutiliser le même `thread_id` dans `configurable`. Le test de reprise
utilise uniquement des données synthétiques et une panne simulée.

## Tests

```bash
PYTHONPATH=runtime python -m unittest tests.test_langgraph_demo -v
```

Les tests sont ignorés si LangGraph n'est pas installé. Ils ne valident pas
l'intégration à un service distant.

## Barrières non négociables

Ce prototype ne peut pas :
- activer `execution_enabled` ou modifier `config/policy.json` ;
- réserver, terminer ou relancer un job dans la file PAPI ;
- appeler un handler métier ou contourner son registre ;
- contacter un prospect, publier, acheter, payer ou traiter une transaction ;
- stocker des secrets ou des données personnelles ;
- déclarer un agent opérationnel.

Toute future connexion au noyau devra passer par des interfaces explicites,
des permissions déjà existantes, des tests d'intégration et une revue de
sécurité. L'activation du worker et les actions externes nécessiteront une
décision distincte du propriétaire.

## Statut

Prototype de code isolé proposé dans une pull request. LangGraph n'est pas
ajouté aux dépendances obligatoires ; aucun service n'est connecté et aucun
agent n'est déployé.
