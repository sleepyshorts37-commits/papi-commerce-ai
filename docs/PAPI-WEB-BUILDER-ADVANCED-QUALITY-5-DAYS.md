# PAPI WEB BUILDER — Cycle qualité avancée sur 5 jours

## Objectif
Renforcer la qualité du générateur multi-pages sur quatre axes mesurables : contraste des textes et états de focus, sémantique HTML, comportement clavier/mouvement réduit, et budgets de poids/performance. Les tests doivent rester déterministes, locaux et sans données réelles.

Ce cycle n'est pas une certification WCAG 2.2 AA, un audit Lighthouse complet, ni une autorisation de production.

## Jour 1 — Contraste des couleurs et tokens sectoriels
- [ ] Mesurer le contraste WCAG des accents des six profils sur leurs surfaces réelles.
- [ ] Corriger les accents utilisés pour du petit texte afin d'atteindre au moins 4,5:1 sur les surfaces prévues.
- [ ] Ajouter un contrôle de contraste dans le rapport qualité multi-pages.
- [ ] Ajouter des tests unitaires pour les six secteurs et une vérification Chromium du texte accentué.
- Livrable : tokens lisibles avec preuve automatisée, sans prétendre à un audit complet.

## Jour 2 — Sémantique et structure de toutes les pages
- [ ] Vérifier les landmarks, noms de navigation, titres uniques et hiérarchie des titres.
- [ ] Vérifier les noms accessibles des liens et les attributs des liens de navigation courante.
- [ ] Contrôler toutes les routes d'un site synthétique, pas seulement l'accueil.
- Livrable : rapport de structure sémantique reproductible.

## Jour 3 — Clavier, mouvement réduit et comportement responsive
- [ ] Tester le lien d'évitement et le parcours clavier sur les pages.
- [ ] Vérifier le respect de `prefers-reduced-motion` dans les styles calculés.
- [ ] Renforcer les assertions de layout mobile et tablette sur les composants de navigation.
- Livrable : contrôles navigateur sur interaction et mouvement.

## Jour 4 — Budgets de performance et réseau
- [ ] Définir des budgets explicites pour HTML/CSS, nombre de requêtes et taille du DOM sur le site synthétique.
- [ ] Vérifier l'absence de requêtes tierces et de ressources bloquées.
- [ ] Mesurer les métriques navigateur disponibles sans transformer une mesure locale en Core Web Vitals terrain.
- Livrable : budget de performance de laboratoire et limites clairement documentées.

## Jour 5 — CI, recette et rapport
- [ ] Intégrer tous les contrôles dans la CI existante.
- [ ] Exécuter les suites core, registry, docs et Chromium sur le commit final.
- [ ] Conserver les artefacts utiles et produire le rapport de recette.
- [ ] Mettre à jour la roadmap avec les preuves exactes.
- Livrable : décision PASS/FAIL limitée aux critères réellement testés.

## Garde-fous
- Site de test synthétique ; serveur loopback en lecture seule.
- Aucune donnée client, clé, connexion distante, paiement ou service tiers.
- Pas de merge, publication ou déploiement sans autorisation explicite.
- Les mesures de laboratoire ne sont pas des données Core Web Vitals d'utilisateurs réels.
- Le contraste automatisé de quelques tokens ne certifie pas toutes les combinaisons de couleurs ni WCAG 2.2 AA.
