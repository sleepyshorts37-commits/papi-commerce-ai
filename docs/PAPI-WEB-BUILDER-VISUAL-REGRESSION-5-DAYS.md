# PAPI WEB BUILDER — régression visuelle et cohérence responsive (5 jours)

## Objectif
Renforcer la détection automatisée des régressions de mise en page sur les routes générées, en Chromium et sur trois formats d'écran. Le cycle privilégie des assertions géométriques et de styles calculés déterministes, ainsi que des captures CI traçables. Il ne prétend pas fournir une comparaison pixel-perfect ni une certification d'accessibilité.

## Jour 1 — Baseline géométrique multi-viewport
- [x] Mesurer header, hero, visuel du hero, titre et cartes de contenu sur mobile, tablette et desktop.
- [x] Détecter débordements horizontaux et composants invisibles ou écrasés par des seuils géométriques.
- [x] Vérifier la génération et la présence de captures non vides (artefact CI final, 3 captures, ID `14070778672`).
- **Statut Jour 1 :** contrat de géométrie ajouté dans `tests/browser/test_preview_browser.py` sur `2a1df36` ; validé par la suite Chromium finale. Ce contrôle est un garde-fou structurel, pas une comparaison pixel-perfect.
- Livrable : assertions de géométrie responsive exécutées dans Chromium.

## Jour 2 — Cohérence des composants et du design system
- [x] Vérifier dans Chromium les tokens calculés (ink/accent/surface), polices locales, taille/poids du H1, colonnes, gaps, padding, bordures et rayons des cartes.
- [x] Contrôler l'ordre des cartes et l'absence de chevauchement hero/sections/cartes sur mobile, tablette et desktop.
- **Statut Jour 2 :** test `test_component_design_tokens_spacing_and_non_overlap` ajouté et validé par la suite Chromium finale.
- Livrable : matrice de cohérence calculée des composants sur trois viewports.

## Jour 3 — Couverture des secteurs
- [x] Générer dans le test Chromium un projet synthétique distinct pour chacun des six secteurs supportés.
- [x] Vérifier les tokens primary/accent/surface, la classe de secteur, la variante de hero, le visuel, les trois cartes et la route Contact.
- [x] Contrôler chaque profil sur mobile (390×844), tablette (768×1024) et desktop (1440×900), y compris l'absence de débordement horizontal.
- **Statut Jour 3 :** `test_all_six_sector_profiles_render_responsively` ajouté ; défaut e-commerce mobile corrigé puis suite Chromium finale PASS.
- Livrable : test Chromium multi-secteurs sur 18 combinaisons secteur/viewport.

## Jour 4 — Régression des interactions et états
- [x] Tester sur la page secondaire une section FAQ interactive (ouverture native details/summary), un CTA interne, la navigation de retour et la visibilité du focus clavier.
- [x] Vérifier les sections configurables intro/FAQ/CTA, un titre et un contenu longs ainsi qu'un libellé CTA long sur mobile, tablette et desktop ; absence de débordement horizontal.
- **Statut Jour 4 :** `test_custom_sections_interactions_long_content_and_internal_cta` ajouté et validé dans la suite Chromium finale (13 tests PASS).
- Livrable : test Chromium de parcours et robustesse des contenus configurables.

## Jour 5 — CI et rapport
- [x] Analyser l'échec Chromium réel du Jour 3/4 : débordement horizontal du profil e-commerce à 390×844 px.
- [x] Ajouter une protection CSS contre les largeurs intrinsèques des enfants de grille et les textes longs ; forcer une colonne fluide du hero sous 800 px (commit `b0d7b58`).
- [x] Relancer core, Chromium, registre et documentation sur le correctif final : quatre workflows PASS sur `b0d7b58`.
- [x] Publier `docs/PAPI-WEB-BUILDER-VISUAL-REGRESSION-REPORT.md` avec les commits, les workflows, l'artefact et les limites ; mettre à jour la roadmap.
- Livrable : dossier de preuves reproductible, correction responsive validée.

## Garde-fous
- Sites et contenus synthétiques uniquement ; Chromium local/CI.
- Pas de requête tierce, de données client, de déploiement, de publication ou de merge.
- Les captures ne constituent pas une validation pixel-perfect entre systèmes d'exploitation.
- Aucune certification WCAG 2.2 AA ni mesure Core Web Vitals terrain n'est revendiquée.
