# PAPI GLOBAL WORK — pipeline unifié de revue

## Point d'entrée
Utiliser `papi_core.global_work_review.review_global_work_opportunities` avec :
- les opportunités déjà collectées (aucune collecte réseau ici) ;
- le registre de sources ;
- les observations de preuves regroupées par identifiant de source ;
- une date de référence et le code pays du demandeur (SN par défaut).

## Étapes
1. Valider le registre et l'unicité des identifiants de source.
2. Examiner les preuves fournies, leurs URL, dates, champs et réviseurs déclarés.
3. Comparer les observations récentes cohérentes relatives aux pays et moyens de paiement avec les déclarations du registre. Toute divergence est signalée comme contradiction.
4. Réutiliser le pipeline qualité/fraîcheur/économie, puis le classement explicable.
5. Produire les compteurs, les raisons, les blocages et les revues de preuves par source.

## Limites
Les preuves ne sont pas téléchargées ni authentifiées. Un nom de réviseur n'est pas une identité vérifiée. La cohérence ne certifie pas une plateforme. Les données de registre et d'annonce restent des déclarations à confirmer sur les pages officielles. Le résultat sert à organiser le travail humain, jamais à accepter une mission ou à postuler.

Aucune action externe, navigation, inscription, candidature, prise de contact, dépense ou transaction. Tous les indicateurs de qualification et de candidature restent faux.
