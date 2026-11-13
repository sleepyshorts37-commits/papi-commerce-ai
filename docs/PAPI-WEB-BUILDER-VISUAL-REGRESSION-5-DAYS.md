# PAPI WEB BUILDER — régression visuelle et cohérence responsive (5 jours)

## Objectif
Renforcer la détection automatisée des régressions de mise en page sur les routes générées, en Chromium et sur trois formats d'écran. Le cycle privilégie des assertions géométriques et de styles calculés déterministes, ainsi que des captures CI traçables. Il ne prétend pas fournir une comparaison pixel-perfect ni une certification d'accessibilité.

## Jour 1 — Baseline géométrique multi-viewport
- [ ] Mesurer header, hero, visuel, grille de contenu et footer sur mobile, tablette et desktop.
- [ ] Détecter débordements horizontaux, éléments hors viewport et composants invisibles/écrasés.
- [ ] Vérifier la génération et la présence de captures non vides.
- Livrable : assertions de géométrie responsive exécutées dans Chromium.

## Jour 2 — Cohérence des composants et du design system
- [ ] Vérifier les tokens calculés, tailles typographiques clés, espacements et rayons des composants.
- [ ] Contrôler l'ordre visuel et l'absence de chevauchement sur les routes.
- Livrable : matrice de cohérence des composants.

## Jour 3 — Couverture des secteurs
- [ ] Générer des projets synthétiques pour les six secteurs.
- [ ] Vérifier les variantes de hero, couleurs calculées et structure des composants.
- [ ] Contrôler le responsive sur les viewports ciblés.
- Livrable : tests navigateur multi-secteurs.

## Jour 4 — Régression des interactions et états
- [ ] Vérifier navigation, CTA, focus, hover/focus-visible et états de menu disponibles.
- [ ] Vérifier que les contenus longs et libellés ne créent pas de débordement.
- Livrable : tests de parcours et robustesse visuelle.

## Jour 5 — CI et rapport
- [ ] Exécuter core, Chromium, registre et documentation sur les changements finaux.
- [ ] Corriger les défauts et publier un rapport PASS/FAIL avec limites.
- [ ] Mettre à jour la roadmap.
- Livrable : dossier de preuves reproductible.

## Garde-fous
- Sites et contenus synthétiques uniquement ; Chromium local/CI.
- Pas de requête tierce, de données client, de déploiement, de publication ou de merge.
- Les captures ne constituent pas une validation pixel-perfect entre systèmes d'exploitation.
- Aucune certification WCAG 2.2 AA ni mesure Core Web Vitals terrain n'est revendiquée.
