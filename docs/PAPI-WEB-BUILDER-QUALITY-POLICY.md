# Politique de niveaux de qualité — PAPI WEB BUILDER

## Principe
PAPI WEB BUILDER ne doit jamais annoncer qu'un site est « prêt pour la production », « professionnel » ou « entreprise-critique » sur la seule base d'une génération réussie ou de tests unitaires. Chaque niveau est attribué uniquement lorsque toutes les preuves cumulatives sont enregistrées, vérifiables et revues.

## Niveaux et critères obligatoires

| Niveau | Critères supplémentaires (les niveaux sont cumulatifs) | Ce que le niveau ne signifie pas |
|---|---|---|
| Prototype | Génération statique, échappement HTML, responsive smoke test, accessibilité structurelle de base, tests automatisés | Pas de validation métier ni de mise en production |
| MVP | Navigation multi-pages, tests navigateur multi-écrans, SEO de base, intégrité de l'export, absence de requêtes tierces non approuvées | Pas de garantie de sécurité ou de conformité légale |
| Production professionnelle | Audit WCAG 2.2 AA humain, revue sécurité indépendante, Core Web Vitals terrain, test sauvegarde/restauration, monitoring/alertes, revue confidentialité/légale, approbation du propriétaire | Pas de certification universelle ni de garantie sans limites |
| Entreprise-critique | Test d'intrusion indépendant, modèle de menace, exercice PRA, SLO/budget d'erreur, revue d'accès, exercice de réponse à incident, revue supply chain, artefacts signés | Ne remplace pas les obligations réglementaires ni la gouvernance du client |

## Enregistrement d'une preuve
Chaque critère exige :
- `status` égal à `passed` ;
- `evidence_ref` : référence réelle vers un rapport, un artefact CI ou un procès-verbal ;
- `verified_at` : date ISO-8601 avec fuseau horaire ;
- `reviewer` : identité du réviseur.

Les statuts `pending`, `failed`, les références vides, les dates invalides/sans fuseau ou les réviseurs absents ne comptent pas comme preuves. Les critères sont cumulatifs. Le moteur retourne le niveau démontré, les preuves manquantes et le refus éventuel du niveau demandé.

## Responsabilités et limites
Les agents peuvent préparer des contrôles et compiler les rapports dans leurs permissions. Ils ne peuvent pas s'auto-attribuer une validation indépendante : les audits humains/externes et l'approbation du propriétaire doivent provenir de personnes autorisées. Un résultat de niveau n'autorise jamais une publication, un achat de domaine, une dépense, une activation d'hébergement ou un contact client. Ces actions nécessitent une approbation distincte.

## Implémentation
Le moteur `runtime/papi_core/quality_gates.py` expose `evaluate_quality_level(evidence, requested_level=None)` et `require_quality_level(evidence, requested_level)`. Le second échoue de manière fermée si les preuves cumulatives ne permettent pas le niveau demandé. Il retourne toujours `publication_authorized: false`.
