# Mission 102 — Sélection des fournisseurs image à quota gratuit

Date : 2026-11-15
Base : Mission 101, commit `b702a7e9268c32caa8332d2966d6291f5910b2f1`.

## Demande
Le propriétaire confirme qu'il souhaite des fournisseurs gratuits avec des limites/quota, capables d'être appelés par les agents pour réaliser les tâches créatives du projet.

## Recherche documentaire
- Cloudflare Workers AI : allocation Free documentée de 10 000 Neurons par jour ; candidat principal API. La consommation dépend du modèle, donc aucun nombre d'images/jour n'est promis.
- Pollinations.ai : accès anonyme gratuit à certains modèles, limité par IP ; documentation indique au moins 45 secondes entre les générations d'images anonymes. Les conditions et modèles gratuits sont susceptibles d'évoluer.
- Hugging Face Spaces ZeroGPU : quota gratuit documenté de 5 minutes GPU par jour ; option secondaire pour essais, à ne pas confondre avec les crédits Inference Providers.

## Livrable
`docs/PAPI-IMAGE-PROVIDERS-FREE-QUOTA.md` définit l'ordre de test, le routage, les limites et les conditions d'activation.

## Décision
Cloudflare Workers AI est le premier fournisseur à intégrer et tester. Pollinations est le candidat de secours ; Hugging Face ZeroGPU est expérimental. Aucun compte n'a été créé, aucune clé demandée, aucune génération API exécutée et aucun déploiement effectué.

## État
- Architecture agents : documentée.
- Politique FREE_ONLY / FREE_QUOTA : documentée.
- Adaptateur image opérationnel : non implémenté.
- Agents actifs : 0.
- Dépenses : 0.
- Publication/déploiement : aucun.
