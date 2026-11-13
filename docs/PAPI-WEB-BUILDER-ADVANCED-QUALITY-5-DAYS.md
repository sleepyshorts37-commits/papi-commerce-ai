# PAPI WEB BUILDER — Cycle qualité avancée sur 5 jours

## Objectif
Renforcer la qualité du générateur multi-pages sur quatre axes mesurables : contraste des textes et états de focus, sémantique HTML, comportement clavier/mouvement réduit, et budgets de poids/performance. Les tests doivent rester déterministes, locaux et sans données réelles.

Ce cycle n'est pas une certification WCAG 2.2 AA, un audit Lighthouse complet, ni une autorisation de production.

## Jour 1 — Contraste des couleurs et tokens sectoriels
- [x] Mesurer le contraste WCAG des accents des six profils sur leurs surfaces réelles.
- [x] Corriger les accents utilisés pour du petit texte afin d'atteindre au moins 4,5:1 sur les surfaces prévues.
- [x] Ajouter un contrôle de contraste dans le rapport qualité multi-pages.
- [x] Ajouter des tests unitaires pour les six secteurs et une vérification Chromium du texte accentué.
- **Statut Jour 1 :** PASS CI sur le commit testé `83092e61fd39612fa5ea448569d93c12a1070b96` ; suite core et Chromium réussies.
- Livrable : tokens lisibles avec preuve automatisée, sans prétendre à un audit complet.

## Jour 2 — Sémantique et structure de toutes les pages
- [x] Ajouter le contrôle Chromium des landmarks, noms de navigation, titres uniques et hiérarchie des titres.
- [x] Vérifier les noms accessibles des liens et l'unicité du lien courant dans la navigation.
- [x] Contrôler les routes accueil, services et contact d'un site synthétique.
- **Statut Jour 2 :** PASS CI sur `83092e61fd39612fa5ea448569d93c12a1070b96`, tests sémantiques exécutés sur `/` et `/contact/`.
- Livrable : rapport de structure sémantique reproductible.

## Jour 3 — Clavier, mouvement réduit et comportement responsive
- [x] Tester le lien d'évitement, son activation clavier et l'indicateur de focus sur toutes les routes générées.
- [x] Vérifier le respect de `prefers-reduced-motion` dans les styles calculés.
- [x] Renforcer les assertions de visibilité de la navigation et de ses liens sur mobile, tablette et desktop.
- **Statut Jour 3 :** PASS CI sur `83092e61fd39612fa5ea448569d93c12a1070b96`, y compris clavier, lien d'évitement, focus, mouvement réduit et trois viewports.
- Livrable : contrôles navigateur sur interaction et mouvement.

## Jour 4 — Budgets de performance et réseau
- [x] Définir des budgets explicites : HTML ≤ 100 Ko, CSS ≤ 100 Ko, maximum 4 requêtes navigateur et 500 nœuds DOM.
- [x] Vérifier l'absence de requêtes tierces et de requêtes échouées.
- [x] Mesurer les tailles encodées, le nombre de ressources et les nœuds DOM via les APIs Performance du navigateur.
- **Statut Jour 4 :** PASS CI sur `83092e61fd39612fa5ea448569d93c12a1070b96`. Budgets HTML/CSS, requêtes, DOM et isolement réseau validés sur les routes synthétiques. Ces mesures restent des seuils de laboratoire, pas des Core Web Vitals terrain.
- Livrable : budget de performance de laboratoire et limites clairement documentées.

## Jour 5 — CI, recette et rapport
- [x] Intégrer tous les contrôles dans la CI existante.
- [x] Exécuter les suites core, registry, docs et Chromium : toutes réussies sur `83092e61fd39612fa5ea448569d93c12a1070b96`.
- [x] Conserver les captures Chromium (`papi-browser-responsive-screenshots`, artefact CI 14067852956) et produire `docs/PAPI-WEB-BUILDER-ADVANCED-QUALITY-REPORT.md`.
- [x] Mettre à jour la roadmap avec les preuves exactes.
- **Statut Jour 5 : PASS** — core 429 tests, Chromium 9 tests, documentation et registre réussis. Rapport : `docs/PAPI-WEB-BUILDER-ADVANCED-QUALITY-REPORT.md`.
- Livrable : décision PASS/FAIL limitée aux critères réellement testés.

## Garde-fous
- Site de test synthétique ; serveur loopback en lecture seule.
- Aucune donnée client, clé, connexion distante, paiement ou service tiers.
- Pas de merge, publication ou déploiement sans autorisation explicite.
- Les mesures de laboratoire ne sont pas des données Core Web Vitals d'utilisateurs réels.
- Le contraste automatisé de quelques tokens ne certifie pas toutes les combinaisons de couleurs ni WCAG 2.2 AA.
