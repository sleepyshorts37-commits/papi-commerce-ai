# PAPI WEB BUILDER — durcissement du serveur de prévisualisation (5 jours)

## Objectif
Renforcer par tests adversariaux le serveur HTTP local de prévisualisation, en restant sur un environnement synthétique et loopback. Ce cycle ne remplace pas une revue indépendante ni un test d'intrusion.

## Jour 1 — Parsing des URL et normalisation des chemins
- [x] Ajouter des cas de test pour UTF-8 invalide après décodage, séparateurs Windows encodés et octets NUL encodés.
- [x] Valider les nouveaux cas en CI sur le commit `e011dd4` (core, Chromium, documentation, registre : PASS).
- Livrable : rejet déterministe des chemins ambigus/malformés.

## Jour 2 — Méthodes HTTP et politique de réponse
- [x] Refuser explicitement OPTIONS et TRACE en plus de POST, PUT, PATCH et DELETE ; vérifier GET et HEAD sur HTML/CSS.
- [x] Vérifier les en-têtes CSP, nosniff, Referrer-Policy et no-store sur HTML et CSS.
- **Statut Jour 2 :** implémentation et tests ajoutés dans `runtime/papi_core/preview_server.py` et `tests/test_preview_server.py` ; CI core, Chromium, registre et documentation : PASS sur `20b38de`.
- Livrable : matrice méthodes/en-têtes vérifiée.

## Jour 3 — Traversée, symlinks et confinement
- [x] Ajouter des tests de traversal doublement encodé, chemins absolus et liens symboliques vers une cible extérieure.
- [x] Vérifier qu'un fichier sentinelle hors racine n'est jamais exposé par HTTP.
- Livrable : tests de confinement du répertoire.

**Statut Jour 3 :** tests ajoutés dans `tests/test_preview_server.py` ; validation CI en attente sur `c11d763`.

## Jour 4 — Robustesse des ressources
- [ ] Tester fichiers absents, répertoires, noms Unicode et types MIME.
- [ ] Vérifier la stabilité du serveur après requêtes invalides et les limites de comportement attendues.
- Livrable : matrice de robustesse des ressources.

## Jour 5 — CI et rapport
- [ ] Exécuter core, registry, docs et Chromium sur le commit final.
- [ ] Corriger les régressions révélées par CI.
- [ ] Publier le rapport PASS/FAIL et mettre à jour la roadmap.
- Livrable : preuve automatisée limitée aux scénarios effectivement testés.

## Garde-fous
- Tests sur fichiers synthétiques uniquement.
- Serveur attaché à loopback, lecture seule, sans données client ni service tiers.
- Aucun déploiement, publication, merge ou test externe.
- Les tests ne constituent pas un audit sécurité indépendant ou une garantie d'absence de vulnérabilité.
