# PAPI WEB BUILDER — Cycle de validation navigateur sur 5 jours

## Objectif du cycle

Faire passer la prévisualisation statique locale d'un service HTTP sécurisé à une chaîne de validation reproductible en navigateur réel, avec couverture des principaux formats d'écran et contrôles d'accessibilité automatisables.

Ce cycle ne constitue ni une certification WCAG, ni une validation de production. Les contrôles automatisés doivent être complétés par une revue humaine avant toute mise en service.

## Jour 1 — Fiabiliser le serveur de prévisualisation

- [x] Lire les résultats CI du commit précédent et identifier l'échec exact.
- [x] Corriger la résolution de la route racine `/` vers `index.html` sans double concaténation.
- [x] Ajouter/compléter les tests HTTP de racine, sous-répertoire et méthode HEAD.
- [x] Vérifier la CI sur le commit correctif (suite cœur, registre et documentation verte).
- Livrable : serveur local cohérent et tests HTTP verts.

## Jour 2 — Installer une base de tests navigateur isolée

- [x] Vérifier la structure CI et séparer les dépendances navigateur des dépendances runtime.
- [x] Ajouter Playwright épinglé dans `requirements-browser-test.txt`.
- [x] Ajouter un workflow GitHub Actions dédié qui installe Chromium et lance les tests.
- [x] Générer un site multi-pages synthétique dans un répertoire temporaire.
- [x] Démarrer et arrêter le serveur de prévisualisation loopback dans les tests.
- [x] Ajouter les premiers tests Chromium sur la page d'accueil, la page secondaire et la feuille CSS.
- [x] Supprimer la dépendance Google Fonts distante du générateur et utiliser des polices système locales ; ajouter un test unitaire et une assertion navigateur interdisant les requêtes tierces.
- [x] Confirmer l'exécution effective du workflow sur le commit de base : tests Chromium d'accueil, route secondaire et CSS verts. Le test responsive ajouté ensuite a révélé une assertion de route à corriger.

## Jour 3 — Couverture responsive et navigation

Implémentation et workflow CI présents. Le premier passage CI a détecté une assertion incorrecte : la route générée se termine par `/contact/index.html`. Correctif appliqué ; la validation de ce correctif est en attente.

- [x] Ajouter les vues mobile (390×844), tablette (768×1024) et desktop (1440×900).
- [x] Vérifier le débordement horizontal, la visibilité des titres et des liens de navigation.
- [x] Vérifier la navigation vers la page secondaire depuis chaque viewport.
- [x] Configurer les captures PNG par viewport comme artefacts CI (rétention 7 jours).
- [ ] Confirmer les trois tests navigateur et la présence des artefacts sur le commit corrigé.
- Livrable : matrice viewport implémentée ; validation CI finale en attente.

## Jour 4 — Contrôles d'accessibilité automatisables

- [x] Ajouter un test Chromium sur les landmarks `main` et `nav`, l'unicité du H1 et le lien d'évitement.
- [x] Vérifier que les liens ont un nom accessible via leur texte ou leurs attributs ARIA.
- [x] Vérifier au clavier que le premier arrêt est visible et possède un indicateur de focus calculé.
- [x] Garder les contrôles autonomes et sans chargement de script tiers ; axe-core n'est pas ajouté à cette étape afin de préserver le mode sans requêtes externes.
- [x] Documenter les limites : contraste, lecteur d'écran, clavier complet et WCAG 2.2 AA nécessitent aussi une revue humaine.
- [ ] Confirmer le nouveau test dans GitHub Actions.
- Livrable : contrôles automatisés structurels et clavier de base, sans revendication de conformité certifiée.

## Jour 5 — Intégration CI et critères d'acceptation

- [ ] Intégrer les tests navigateur à une étape CI dédiée et isolée.
- [ ] Définir les critères bloquants, les artefacts conservés et la gestion des échecs.
- [ ] Exécuter la suite complète sur le commit final et corriger les régressions observées.
- [ ] Mettre à jour la roadmap et le rapport de validation avec les résultats réels.
- Livrable : chaîne de validation navigateur documentée, reproductible et non déployée.

## Garde-fous

- Le serveur de prévisualisation reste lié à loopback et en lecture seule.
- Les tests utilisent uniquement des contenus synthétiques.
- Aucun accès Supabase distant, secret de production, paiement, formulaire connecté ou donnée client.
- Aucune publication, fusion de PR ou mise en production sans autorisation explicite.
- Un résultat axe-core ou une capture d'écran ne vaut pas certification WCAG ni recette humaine.
