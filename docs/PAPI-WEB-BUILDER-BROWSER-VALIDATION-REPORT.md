# PAPI WEB BUILDER — Rapport de validation navigateur

## Décision de recette

**Résultat : PASS pour la chaîne de prévisualisation locale et les contrôles automatisés exécutés sur le commit `e704667230d21f5cb3561bd5647642f55fe467ce`.**

Cette recette valide un aperçu statique local sur Chromium et les contrôles définis ci-dessous. Elle ne certifie pas le produit comme prêt pour production, ne vaut pas audit WCAG 2.2 AA et ne valide aucune fonctionnalité backend ou transactionnelle.

## Preuve CI

Commit testé : `e704667230d21f5cb3561bd5647642f55fe467ce`  
Pull request : [#131](https://github.com/sleepyshorts37-commits/papi-commerce-ai/pull/131) — ouverte, brouillon, non fusionnée.

| Workflow | Exécution | Résultat |
|---|---:|---|
| PAPI core tests | [43484766818](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43484766818) | Réussi — 428 tests Python |
| PAPI registry validation | [43484766821](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43484766821) | Réussi |
| PAPI documentation checks | [43484766876](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43484766876) | Réussi |
| PAPI browser preview tests | [43484767063](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43484767063) | Réussi — 4 tests Chromium |

Le job Chromium a installé Python 3.12 et Chromium, exécuté les quatre tests sans échec, puis téléversé l'artefact de captures. Le job et l'étape d'upload sont tous deux en succès.

## Couverture effectivement testée

- Rendu de la page d'accueil dans Chromium réel.
- Chargement d'une route secondaire et de la feuille CSS partagée.
- Trois viewports : mobile 390×844, tablette 768×1024 et desktop 1440×900.
- Navigation inter-pages, visibilité des éléments essentiels et absence de débordement horizontal.
- Captures PNG téléversées comme artefact CI.
- Landmarks `main` et `nav`, H1 unique, lien d'évitement, noms accessibles des liens et focus clavier visible.
- Génération sans appel Google Fonts externe ; le test unitaire vérifie l'usage des polices système locales.

## Artefact de preuve

- Nom : `papi-browser-responsive-screenshots`
- [Télécharger les captures depuis l'exécution GitHub Actions](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43484767063/artifacts/14066757952)
- Taille constatée : 549 050 octets.
- Rétention configurée : 7 jours.

## Critères d'acceptation

- [x] Suite de tests cœur réussie.
- [x] Validation du registre réussie.
- [x] Validation de la documentation réussie.
- [x] Suite Chromium complète réussie.
- [x] Tests responsive mobile/tablette/desktop exécutés.
- [x] Contrôles structurels et clavier de base exécutés.
- [x] Artefact de captures téléversé.
- [x] Tests basés sur un site synthétique et un serveur local loopback.
- [x] Aucun déploiement, aucune fusion et aucune donnée client réelle.

## Limites et actions restantes avant production

- Revue manuelle de contraste, lecteur d'écran, parcours clavier complet et conformité WCAG 2.2 AA.
- Régression visuelle comparative et mesures Core Web Vitals.
- Revue de sécurité applicative indépendante.
- Validation des formulaires, API, authentification, stockage, intégrations et fonctions transactionnelles — non couvertes par ce prototype statique.
- Revue de la cohérence de la PR #131 : son titre et sa description portent sur la persistance mémoire/chat, alors que cette branche contient également des travaux Web Builder. Ne pas fusionner avant clarification/restructuration de la PR.
- Avertissement CI non bloquant : les actions checkout/setup-python/upload-artifact signalent une dépréciation de Node.js 20 et leur exécution forcée sous Node.js 24. Prévoir une mise à niveau contrôlée des actions.

## Garde-fous conservés

Aucune connexion Supabase distante, aucun secret de production, aucun paiement, aucune donnée personnelle client, aucun déploiement ni publication n'a été utilisé ou activé. Le statut opérationnel reste limité à la génération statique et à l'aperçu local contrôlé.
