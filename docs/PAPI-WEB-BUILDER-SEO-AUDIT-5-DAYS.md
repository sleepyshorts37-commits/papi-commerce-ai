# Cycle de 5 jours — Audit SEO automatisé PAPI WEB BUILDER

## Objectif
Fournir un diagnostic SEO reproductible des sites statiques générés, sans prétendre garantir un classement Google ni publier le site.

## Périmètre des cinq journées
1. Définir les critères bloquants, les avertissements et les limites de l'audit.
2. Implémenter un auditeur HTML local : titre, description, langue, H1, canonical, Open Graph, liens internes et robots.
3. Vérifier le sitemap XML, les chemins, les liens cassés et les fichiers symboliques.
4. Ajouter des tests unitaires couvrant les sites valides, les métadonnées absentes, les liens cassés et les entrées non sûres ; documenter les corrections.
5. Exécuter les tests ciblés et la CI complète, publier le rapport final et mettre à jour la roadmap.

## Critères de réussite
- Audit en lecture seule, sans réseau ni exécution de scripts.
- Résultat structuré par page, avec erreurs bloquantes et avertissements séparés.
- Les métadonnées sociales et canonical sont diagnostiquées sans être présentées comme des facteurs de classement garantis.
- Aucun domaine ou URL public n'est inventé.
- Tests reproductibles et rapport honnête des résultats CI.

## Garde-fous
L'audit ne remplace pas Google Search Console, une analyse de backlinks, une vérification d'indexation, un audit éditorial humain, ni une mesure terrain des performances. Aucun déploiement, soumission aux moteurs, publication ou contact externe n'est autorisé par ce cycle.

## Suivi
- [x] Jour 1 — spécification du périmètre et des critères.
- [x] Jour 2 — moteur d'audit SEO local (`runtime/papi_core/seo_audit.py`).
- [x] Jour 3 — six tests de conformité et de sécurité (`tests/test_seo_audit.py`).
- [x] Jour 4 — guide de correction SEO ajouté (`docs/PAPI-WEB-BUILDER-SEO-GUIDE.md`).
- [ ] Jour 5 — CI complète et rapport final.
