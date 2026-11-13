# Rapport de recette — PAPI Web Builder, qualité avancée

Date de validation : 2026-11-13  
Commit testé : `83092e61fd39612fa5ea448569d93c12a1070b96`

## Résultat CI

| Workflow | Run GitHub | Résultat |
|---|---:|---|
| Core tests | [43488603660](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43488603660) | PASS — 429 tests |
| Chromium preview | [43488603672](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43488603672) | PASS — 9 tests |
| Documentation | [43488603678](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43488603678) | PASS |
| Registry validation | [43488603817](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43488603817) | PASS |

Le workflow core inclut également l'application du schéma Supabase sur PostgreSQL jetable. Les étapes de tests et de validation de schéma se sont terminées avec succès.

Le workflow Chromium a exécuté les contrôles de contraste, structure sémantique, navigation clavier, mouvement réduit, responsive et budgets de performance. Les captures d'écran ont été archivées dans l'artefact `papi-browser-responsive-screenshots` (546 722 octets) : [artefact CI](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43488603672/artifacts/14067852956).

## Critères testés

- Contraste : six accents sectoriels contrôlés, cible de 4,5:1 sur les surfaces testées.
- Sémantique : routes synthétiques Accueil et Contact, landmarks, titres, liens accessibles et indication de page courante.
- Clavier : lien d'évitement, activation clavier, cible `#main-content` visible et focus visible.
- Mouvement : vérification de `prefers-reduced-motion`.
- Responsive : viewports 390×844, 768×1024 et 1440×900.
- Performance de laboratoire : HTML ≤ 100 Ko, CSS ≤ 100 Ko, maximum 4 requêtes navigateur et 500 nœuds DOM.
- Réseau : aucune requête tierce ni requête échouée sur les pages testées.

## Limites et exclusions

Cette recette est limitée aux pages et scénarios synthétiques couverts par les tests. Elle ne constitue pas une certification WCAG 2.2 AA, un audit complet par lecteur d'écran, une revue manuelle exhaustive du clavier, un audit de sécurité, ni une mesure de Core Web Vitals auprès d'utilisateurs réels. Les budgets sont des seuils internes de laboratoire et devront être ajustés sur des sites réels.

Aucun déploiement, publication, merge, connexion à un service externe ou traitement de données client n'a été effectué.

## Décision

**PASS — critères automatisés du cycle avancé validés sur le commit indiqué.**  
La mise en production reste hors périmètre et nécessite une décision distincte ainsi que des audits complémentaires.
