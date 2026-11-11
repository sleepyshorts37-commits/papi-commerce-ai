# Noyau de coordination PAPI — version 0.1

## Ce qui est livré
Le module Python `runtime/papi_core` fournit un premier contrôle déterministe des registres : lecture du catalogue d'agents, vérification des tâches, détection des agents inconnus, contrôle des approbations et exigence de preuves pour clôturer une tâche. Il propose également une recherche des agents candidats par département.

## Utilisation locale
Depuis la racine du dépôt, avec Python 3 :

```bash
PYTHONPATH=runtime python -m papi_core validate
PYTHONPATH=runtime python -m papi_core route Prospection
PYTHONPATH=runtime python -m unittest discover -s tests -v
```

## Limites de sécurité
Le routage est une recommandation documentaire, pas une affectation ni une exécution. Le noyau ne lance aucun agent IA, ne contacte aucun prospect, ne lit aucun compte externe et ne manipule aucun paiement. Les actions externes sont désactivées par défaut dans `config/policy.json`.

## Prochaine évolution
Connecter ce noyau à un registre d'événements et à un orchestrateur persistant, puis intégrer un modèle IA uniquement après définition du fournisseur, des limites gratuites, des secrets et des autorisations. Toute action vers un tiers restera soumise à la politique de validation.
