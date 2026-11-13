# PAPI WEB BUILDER — durcissement du serveur de prévisualisation (5 jours)

## Objectif
Renforcer par tests adversariaux le serveur HTTP local de prévisualisation, en restant sur un environnement synthétique et loopback. Ce cycle ne remplace pas une revue indépendante ni un test d'intrusion.

## Jour 1 — Parsing des URL et normalisation des chemins
- [x] Ajouter des cas de test pour UTF-8 invalide après décodage, séparateurs Windows encodés et octets NUL encodés.
- [ ] Valider les nouveaux cas en CI sur le commit du jour.
- Livrable : rejet déterministe des chemins ambigus/malformés.

## Jour 2 — Méthodes HTTP et politique de réponse
- [ ] Couvrir toutes les méthodes HTTP non autorisées et les réponses HEAD/GET.
- [ ] Vérifier systématiquement les en-têtes de sécurité sur HTML et ressources statiques.
- Livrable : matrice méthodes/en-têtes vérifiée.

## Jour 3 — Traversée, symlinks et confinement
- [ ] Étendre les tests de traversal encodé, double encodage, chemins absolus et liens symboliques.
- [ ] Vérifier qu'aucun contenu hors racine ne peut être lu.
- Livrable : tests de confinement du répertoire.

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
