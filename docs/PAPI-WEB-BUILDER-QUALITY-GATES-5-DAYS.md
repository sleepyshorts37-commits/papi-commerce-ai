# PAPI WEB BUILDER — niveaux de qualité et portes de livraison (5 jours)

## Objectif
Définir des niveaux de maturité vérifiables et empêcher toute déclaration de niveau sans preuves traçables. Un résultat de qualité ne constitue jamais, à lui seul, une autorisation de déploiement ou de publication.

## Jour 1 — Matrice des niveaux
- [x] Définir Prototype, MVP, Production professionnelle et Entreprise-critique.
- [x] Séparer les contrôles automatisables des audits indépendants et validations humaines.
- [x] Définir le format minimal d'une preuve : statut PASS, référence vérifiable, horodatage avec fuseau et réviseur identifié.
- Livrable : matrice cumulative documentée.

## Jour 2 — Moteur de décision fail-closed
- [x] Ajouter un registre versionné des critères cumulatifs.
- [x] Refuser les preuves absentes, en attente, échouées, non horodatées ou sans réviseur.
- [x] Calculer le niveau le plus élevé démontré et refuser explicitement le niveau demandé s'il n'est pas prouvé.
- [x] Garantir que le moteur n'autorise jamais une publication.
- Livrable : `runtime/papi_core/quality_gates.py`.

## Jour 3 — Tests de non-régression et anti-déclaration abusive
- [x] Tester l'absence de preuves, les critères manquants, les preuves périmées de forme, les statuts pending et les horodatages sans fuseau.
- [x] Tester les niveaux MVP, production et entreprise comme exigences cumulatives.
- [x] Tester le refus des niveaux inconnus et des entrées mal formées.
- Livrable : `tests/test_quality_gates.py`.

## Jour 4 — Documentation opérationnelle
- [x] Définir comment produire, stocker et réviser les preuves réelles.
- [x] Définir les limites : pas de certification automatique WCAG, audit sécurité, mesure terrain ou autorisation de publication.
- [x] Relier les critères aux rapports de recette existants.
- Livrable : registre de critères et guide de preuve.

## Jour 5 — CI, rapport et roadmap
- [x] Exécuter les tests ciblés : 8/8 tests quality_gates PASS ; suite core globale bloquée par un import manquant de papi_core.site_architecture sur la base main initiale (run 43497400577).
- [ ] Corriger ou contourner le problème de base CI et relancer la suite complète.
- [x] Publier un rapport intermédiaire précis (docs/PAPI-WEB-BUILDER-QUALITY-GATES-REPORT.md) ; clôture finale et mise à jour de roadmap restent conditionnées à la CI complète.
- Livrable : dossier de preuves reproductible.

## Matrice cumulative des critères

### Prototype
- Génération statique déterministe.
- Échappement HTML et contrôle des entrées.
- Smoke test responsive.
- Accessibilité structurelle de base.
- Tests automatisés exécutés.

### MVP
Tous les critères Prototype, plus :
- Navigation multi-pages interne vérifiée.
- Matrice navigateur mobile/tablette/desktop.
- Métadonnées SEO et sitemap vérifiés.
- Export limité aux fichiers autorisés et intégrité vérifiée.
- Absence de requêtes tierces non approuvées.

### Production professionnelle
Tous les critères MVP, plus :
- Audit WCAG 2.2 AA par une personne compétente, avec périmètre et rapport.
- Revue sécurité indépendante et remédiation des constats bloquants.
- Core Web Vitals mesurés sur données terrain représentatives.
- Test de sauvegarde et restauration.
- Monitoring et alertes testés.
- Revue confidentialité / obligations légales applicable au site.
- Approbation explicite du propriétaire pour la livraison.

### Entreprise-critique
Tous les critères Production professionnelle, plus :
- Test d'intrusion indépendant.
- Modèle de menace documenté.
- Exercice de reprise après sinistre.
- SLO et budget d'erreur approuvés.
- Revue périodique des accès.
- Exercice de réponse à incident.
- Revue de chaîne d'approvisionnement logicielle.
- Artefacts de livraison signés et vérifiables.

## Format d'une preuve
Chaque critère doit posséder un enregistrement avec `status=passed`, `evidence_ref` non vide, `verified_at` ISO-8601 avec fuseau horaire et `reviewer` non vide. Un lien de preuve doit pointer vers un rapport, un artefact CI ou un procès-verbal réellement consultable. Une simple déclaration d'agent ne suffit pas.

## Garde-fous
- Les preuves doivent être réelles, reproductibles et adaptées au périmètre du site.
- Une preuve absente, échouée, en attente, non datée ou sans réviseur bloque le niveau.
- Les niveaux sont cumulatifs : un niveau supérieur ne compense jamais un contrôle inférieur manquant.
- L'évaluation ne déploie, ne publie, ne contacte personne et ne dépense rien.


## Note de validation CI
La première exécution sur la branche par rapport à main a échoué avant le chargement des tests du générateur multi-pages, car main ne contient pas encore le module papi_core.site_architecture. Cette limitation concerne la base de comparaison, pas le moteur de portes de qualité. La revue est donc rattachée à la branche de coordination qui contient déjà le socle WEB BUILDER ; la CI doit être relancée sur cette base avant clôture.
