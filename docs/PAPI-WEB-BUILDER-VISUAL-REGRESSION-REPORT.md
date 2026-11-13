# Rapport — régression visuelle et cohérence responsive PAPI WEB BUILDER

## Résultat
Cycle de cinq journées terminé. Les quatre workflows GitHub Actions sont PASS sur le commit de correction final `b0d7b58bc65089b2dfd8660731df8921d6d9f538` :
- Core tests : run `43494714730` — PASS.
- Chromium preview : run `43494714637` — PASS, 13 tests exécutés.
- Registry validation : run `43494714666` — PASS.
- Documentation checks : run `43494714658` — PASS.

Les captures responsive ont été produites et téléversées comme artefact `papi-browser-responsive-screenshots`, ID `14070778672` (3 captures, archive de 546 722 octets).

## Travaux couverts
1. Contrat géométrique Chromium sur mobile 390×844, tablette 768×1024 et desktop 1440×900 : header, hero, visuel, titre, cartes, visibilité et absence de débordement horizontal.
2. Contrat de composants : tokens calculés, polices, hiérarchie typographique, grille, espacements, bordures, rayons, ordre et chevauchements.
3. Six secteurs générés séparément — corporate, ecommerce, hospitality, professional_services, education et health — vérifiés sur les trois viewports, soit 18 combinaisons secteur/écran.
4. Parcours de sections configurables sur la page secondaire : intro, FAQ interactive native, CTA interne, navigation retour, focus clavier, contenu et libellés longs, sans débordement.
5. Génération de captures mobile/tablette/desktop dans le workflow Chromium.

## Défaut trouvé et correction
Les exécutions initiales du test multi-secteurs ont échoué sur le profil e-commerce en mobile (overflow horizontal à 390 px). Le test de Jour 4 a également reproduit cet échec, alors que le parcours des sections configurables passait.
Le CSS généré a été renforcé dans `runtime/papi_core/multi_page_builder.py` : contraintes `min-width:0`/largeur maximale pour les enfants de grille, retour à la ligne des contenus longs et grille du hero à une colonne sous 800 px.
Après correction, les 13 tests Chromium passent et les quatre workflows sont verts sur le commit final.

## Commits de livraison
- Tests Chromium et parcours : `b8a7788fa6236827ef7eb510ee36f87db6a5e07f`.
- Correctif responsive final : `b0d7b58bc65089b2dfd8660731df8921d6d9f538`.
- Plan du cycle : `6ef560c1b2f6191665e94993ea0e8bff8d11ed4e`.
- Roadmap : `0b53a347235a4f9bb88ba5b13b2af3a5b56b0026`.

## Limites
- Il s'agit d'assertions structurelles, de styles calculés et d'interactions Chromium ; aucune comparaison d'images pixel-perfect n'est implémentée.
- Les captures servent de preuves visuelles, pas de seuil de différence pixel.
- Pas de certification WCAG 2.2 AA, d'audit complet lecteur d'écran/clavier, de test multi-navigateurs ou de mesure Core Web Vitals terrain.
- Les sites et données utilisés sont synthétiques ; aucune publication, fusion ou mise en production n'a été réalisée.

## Conclusion
Cycle terminé à 100 %. Correctif responsive confirmé par les quatre workflows CI PASS sur le commit final. Aucun merge ni déploiement.
