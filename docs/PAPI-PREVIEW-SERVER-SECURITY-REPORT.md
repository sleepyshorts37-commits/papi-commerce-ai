# Rapport — durcissement du serveur de prévisualisation PAPI

## Résultat
Cycle de cinq jours terminé sur le plan d'implémentation et de validation automatisée. Les tests ont été exécutés sur un serveur local attaché à loopback, avec des fichiers synthétiques. Aucun déploiement ni accès à des données client.

## Couverture vérifiée

### URL et chemins
- UTF-8 invalide après décodage, séparateurs Windows encodés et octets NUL encodés.
- Traversal direct et doublement encodé.
- Chemins absolus de type Unix et Windows.
- Liens symboliques internes et vers une cible extérieure.
- Fichier sentinelle extérieur non divulgué par HTTP.

### Méthodes et réponses HTTP
- GET et HEAD pour HTML et CSS.
- Refus des méthodes POST, PUT, PATCH, DELETE, OPTIONS et TRACE (405).
- En-têtes CSP, X-Content-Type-Options, Referrer-Policy et Cache-Control vérifiés.

### Robustesse des ressources
- Fichiers absents et chemins désignant des répertoires.
- Nom de fichier Unicode et type MIME text/plain.
- Disponibilité du serveur après des requêtes invalides et des ressources absentes.

## Preuves CI

Sur le commit de tests `0b7498aabf73fcb409322ede43b82c077b9704fd` :
- Core tests : PASS — [run 43491775305](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43491775305).
- Chromium preview : PASS — [run 43491775363](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43491775363).
- Registry validation : PASS — [run 43491775206](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43491775206).
- Documentation checks : PASS — [run 43491775184](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/43491775184).

Les quatre workflows sont terminés avec conclusion success. Les journaux détaillés restent consultables dans GitHub Actions.

## Limites
- Les tests ne constituent pas un audit de sécurité indépendant, un test d'intrusion, ni une garantie d'absence de vulnérabilité.
- Ils ne couvrent pas toutes les plateformes, toutes les configurations de système de fichiers, ni les courses TOCTOU possibles.
- La validation ne certifie pas la sécurité d'un éventuel serveur exposé sur Internet.
- Aucun déploiement, publication, merge ou test sur un service externe n'a été effectué.

## Conclusion
Les scénarios automatisés définis dans ce cycle sont PASS sur les workflows listés ci-dessus. Le serveur reste un aperçu local, loopback et en lecture seule. Toute exposition réseau ou mise en production exige une revue distincte.
