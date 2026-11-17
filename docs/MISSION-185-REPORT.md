# Mission 185 — Fiabilisation de la frontière PAPI CONNECT

## Objectif
Renforcer la fiabilité de l'interface commune d'adaptateurs avant toute intégration d'un fournisseur externe. Cette mission reste entièrement locale et sans réseau.

## Constat initial
La passerelle vérifiait les métadonnées principales de l'adaptateur, mais n'exigeait pas que sa méthode `generate` soit appelable. Une exception inattendue levée par un adaptateur pouvait remonter directement à l'appelant, avec un diagnostic interne potentiellement sensible. Aucun retry n'était exécuté aujourd'hui ; cette propriété devait être explicitée pour éviter d'ajouter plus tard une répétition aveugle d'un appel dont le résultat pourrait être ambigu.

## Changements
- Refus à l'enregistrement d'un adaptateur sans méthode `generate` appelable.
- Normalisation des exceptions d'exécution en message générique sans exposer le diagnostic du fournisseur.
- Normalisation des erreurs inattendues de validation des résultats.
- Aucun retry automatique après échec ; l'appelant doit réconcilier un résultat incertain avant toute nouvelle tentative.
- Deux tests de régression : méthode manquante et exception interne non divulguée, avec vérification d'un seul appel.
- Documentation PAPI CONNECT, roadmap et liens README actualisés.
- Workflows core, registry et documentation explicitement déclenchés sur la branche de cette mission.

## Vérification
Commandes couvertes par la CI :
```sh
PYTHONPATH=runtime python -m unittest tests.test_connectors -v
PYTHONPATH=runtime python -m unittest discover -s tests -v
PYTHONPATH=runtime python -m papi_core validate
```
Le statut des workflows doit être lu sur le SHA final de cette branche ; aucun succès n'est présumé dans ce document avant retour de GitHub Actions.

## Limites
- Aucun adaptateur externe n'est autorisé.
- Aucun compte, secret, credential, endpoint distant, dépendance ou dépense n'a été ajouté.
- Aucun agent n'a reçu d'outil et aucun worker n'a été activé.
- L'intégration d'un fournisseur réel reste bloquée jusqu'à la sélection et l'autorisation explicites du propriétaire, avec vérification des coûts, quotas, conditions et disponibilité au Sénégal.
