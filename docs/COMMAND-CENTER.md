# PAPI COMMAND CENTER — version locale 0.1

## Objectif

Le tableau de bord consolide les registres locaux et le briefing d'Astou dans une sortie JSON lisible par un terminal ou une future interface web.

## Lancer

Depuis la racine du dépôt :

```bash
PYTHONPATH=runtime python -m papi_core dashboard
```

La commande affiche notamment :
- le nombre d'agents et leur répartition par statut ;
- le nombre de tâches et leur répartition par statut ;
- les tâches ouvertes, les approbations en attente et les tâches sans responsable valide ;
- le briefing calculé d'Astou ;
- l'état de configuration Supabase sans afficher de secret.

## Sécurité et limites

Version locale en lecture seule. Elle n'écrit aucun fichier, ne démarre aucun worker, ne contacte aucun service et ne déclenche aucune communication ni opération financière. La présence de variables d'environnement ne prouve pas que Supabase est joignable ou que les clés sont valides.

Ce n'est pas encore une interface web hébergée, ni un système de supervision temps réel. Les agents restent documentaires ou planifiés tant qu'un runtime réel n'est pas déployé.
