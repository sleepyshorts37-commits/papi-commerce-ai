# PAPI WEB BUILDER — Cycle de validation navigateur sur 5 jours

## Objectif du cycle

Faire passer la prévisualisation statique locale d'un service HTTP sécurisé à une chaîne de validation reproductible en navigateur réel, avec couverture des principaux formats d'écran et contrôles d'accessibilité automatisables.

Ce cycle ne constitue ni une certification WCAG, ni une validation de production. Les contrôles automatisés doivent être complétés par une revue humaine avant toute mise en service.

## Jour 1 — Fiabiliser le serveur de prévisualisation

- [x] Lire les résultats CI du commit précédent et identifier l'échec exact.
- [x] Corriger la résolution de la route racine `/` vers `index.html` sans double concaténation.
- [ ] Ajouter/compléter les tests HTTP de racine, sous-répertoire et méthode HEAD.
- [ ] Vérifier la CI sur le commit correctif.
- Livrable : serveur local cohérent et tests HTTP verts.

## Jour 2 — Installer une base de tests navigateur isolée

- [ ] Vérifier les dépendances et la disponibilité Playwright dans l'environnement CI.
- [ ] Ajouter une configuration Playwright minimale, avec navigateur Chromium épinglé.
- [ ] Construire un site multi-pages synthétique dans un répertoire temporaire.
- [ ] Démarrer et arrêter le serveur de prévisualisation dans le cycle de test, sans écoute réseau externe.
- Livrable : premier test navigateur reproductible, sans données client ni service distant.

## Jour 3 — Couverture responsive et navigation

- [ ] Tester les vues mobile (390×844), tablette (768×1024) et desktop (1440×900).
- [ ] Vérifier l'absence de débordement horizontal, la visibilité des titres et des liens de navigation.
- [ ] Vérifier les liens entre pages, les feuilles CSS et les routes profondes.
- [ ] Produire des captures d'écran comme artefacts CI, sans les considérer seules comme preuve de qualité.
- Livrable : matrice viewport documentée et tests de navigation.

## Jour 4 — Contrôles d'accessibilité automatisables

- [ ] Contrôler la présence des landmarks, d'un titre principal unique, du lien d'évitement et des noms accessibles.
- [ ] Contrôler le focus clavier visible et l'ordre de navigation de base.
- [ ] Ajouter axe-core si son installation est compatible avec la chaîne CI et ses licences.
- [ ] Documenter les limites : contraste, lecteur d'écran, clavier complet et WCAG 2.2 AA nécessitent aussi une revue humaine.
- Livrable : rapport automatisé de contrôles, sans revendication de conformité certifiée.

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
