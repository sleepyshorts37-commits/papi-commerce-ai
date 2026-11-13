# PAPI WEB BUILDER — Cycle de validation navigateur sur 5 jours

## Objectif
Valider de manière reproductible l'aperçu statique local dans Chromium, les viewports usuels, quelques contrôles d'accessibilité automatisables et l'intégration CI. Ce cycle ne constitue ni une certification WCAG, ni une recette de production.

## Jour 1 — Fiabiliser le serveur de prévisualisation
- [x] Corriger la résolution de la route racine vers `index.html`.
- [x] Compléter les tests HTTP GET/HEAD, ressources et chemins interdits.
- [x] Valider la CI du correctif.
- **Résultat :** serveur loopback en lecture seule et tests HTTP couverts.

## Jour 2 — Base navigateur isolée
- [x] Épingler Playwright dans `requirements-browser-test.txt`, hors dépendances runtime.
- [x] Ajouter un workflow GitHub Actions qui installe Chromium.
- [x] Générer un site synthétique temporaire et tester accueil, route secondaire et CSS.
- [x] Retirer les requêtes Google Fonts externes et tester l'usage de polices système.
- **Résultat :** tests Chromium exécutés en CI.

## Jour 3 — Responsive et navigation
- [x] Viewports mobile 390×844, tablette 768×1024 et desktop 1440×900.
- [x] Vérifier visibilité, débordement horizontal et navigation inter-pages.
- [x] Captures PNG téléversées en artefact CI, rétention 7 jours.
- **Résultat :** validé sur le commit `e704667230d21f5cb3561bd5647642f55fe467ce`.

## Jour 4 — Accessibilité automatisable
- [x] Landmarks main/nav, H1 unique et lien d'évitement.
- [x] Noms accessibles des liens et focus clavier visible.
- [x] Aucun script tiers requis pour ces contrôles.
- [x] Documenter les limites et la revue humaine nécessaire.
- **Résultat :** test Chromium dédié exécuté avec succès. Pas de revendication WCAG.

## Jour 5 — CI et recette
- [x] Workflow navigateur isolé et exécution sur le commit final.
- [x] Critères d'acceptation et garde-fous consignés.
- [x] Suite cœur, registre, documentation et Chromium réussis.
- [x] Artefact de captures confirmé.
- [x] Rapport final créé : `docs/PAPI-WEB-BUILDER-BROWSER-VALIDATION-REPORT.md`.
- **Résultat :** recette automatisée PASS pour le périmètre défini ; pas de go-live.

## Preuves CI
Commit : `e704667230d21f5cb3561bd5647642f55fe467ce`.
- Core : [43484766818](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43484766818) — 428 tests réussis.
- Registry : [43484766821](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43484766821) — réussi.
- Docs : [43484766876](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43484766876) — réussi.
- Chromium : [43484767063](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43484767063) — 4 tests réussis.
- Captures : artefact `papi-browser-responsive-screenshots`, 549 050 octets, rétention 7 jours.

## Garde-fous et limites
- Aperçu local loopback, lecture seule ; contenu de test synthétique.
- Aucun projet Supabase distant, secret, paiement, formulaire connecté ou donnée client.
- Aucun merge, déploiement ou publication sans autorisation.
- Contraste, lecteur d'écran, clavier complet, WCAG 2.2 AA, Core Web Vitals et revue sécurité restent à valider manuellement/ultérieurement.
- La PR #131 reste ouverte en brouillon ; son intitulé/description ne reflètent pas clairement les changements Web Builder et doivent être clarifiés avant fusion.
