# PAPI GLOBAL WORK — classement des opportunités

## API
`papi_core.global_work_ranking.rank_global_work_opportunities(...)` classe les candidats déjà fournis, en réutilisant les contrôles de qualité, de fraîcheur et d'économie du pipeline. Le registre des sources validé et les revues de preuves sont fournis explicitement par l'appelant.

## Barème déterministe v1
- Publication fraîche : +20 ; inconnue : -5 ; périmée : -15 ; date future : blocage.
- Données de base complètes : +15 ; incomplètes : -10.
- Pays du demandeur explicitement listé : +15 ; non listé : blocage ; inconnu : -10.
- Données économiques complètes : +20 ; incomplètes : -10.
- Revenu net estimé positif : +10 ; revenu net non positif : blocage.
- Revenu horaire net positif : +10.
- Source vérifiée et active : +15 ; source non active/non vérifiée ou absente : pénalité.
- Preuves cohérentes à revoir humainement : +5 ; absentes/insuffisantes : -5 ; contradictions : blocage.

Le score est plafonné entre 0 et 100. Les rangs sont triés par score décroissant, puis identifiant et URL pour garantir un ordre stable. Les montants horaires ne sont pas comparés entre devises : le score n'est ni une probabilité ni une promesse de revenu.

## Décision et limites
`priority_for_human_review` signifie uniquement qu'un dossier mérite d'être examiné en premier. Il ne signifie jamais que l'offre est authentique, disponible, sûre, admissible ou rentable en pratique. Toute inconnue reste explicitement signalée et l'approbation humaine reste obligatoire. Les sources absentes du registre ne sont pas considérées comme vérifiées.

Aucune navigation réseau, candidature, inscription, prise de contact, création de compte, dépense ou transaction n'est réalisée. Les champs de résultat `qualified` et `application_submitted` restent toujours faux.
