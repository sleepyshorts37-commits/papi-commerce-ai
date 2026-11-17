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
CI de confirmation vérifiée sur le SHA `5a79e683bb662f91351d7c684a4693a7cd412a47` :
- [PAPI core tests — run #2803](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/44047749582) : succès ; **241 tests Python réussis** (`Ran 241 tests`, `OK`).
- [PAPI registry validation — run #863](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/44047749569) : succès.
- [PAPI documentation checks — run #832](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/44047749593) : succès.
- Le job PostgreSQL jetable du workflow core est terminé avec succès. Aucun projet Supabase distant n'a été utilisé.

## Limites
- Aucun adaptateur externe n'est autorisé.
- Aucun compte, secret, credential, endpoint distant, dépendance ou dépense n'a été ajouté.
- Aucun agent n'a reçu d'outil et aucun worker n'a été activé.
- L'intégration d'un fournisseur réel reste bloquée jusqu'à la sélection et l'autorisation explicites du propriétaire, avec vérification des coûts, quotas, conditions et disponibilité au Sénégal.
