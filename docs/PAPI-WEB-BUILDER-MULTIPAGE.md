# Génération multi-pages — PAPI WEB BUILDER

## Implémentation

Le module `runtime/papi_core/multi_page_builder.py` consomme le contrat validé par `build_site_architecture` et génère réellement une arborescence statique :
- `index.html` pour l'accueil et `<slug>/index.html` pour les pages secondaires ;
- navigation commune, état actif accessible et fil d'Ariane ;
- feuille CSS partagée et responsive ;
- titres et descriptions SEO par page ;
- `sitemap.xml` et manifeste des fichiers générés.

La génération est déterministe. Les contenus sont échappés en HTML, les routes proviennent exclusivement du contrat de slugs sûrs et aucun JavaScript fourni par l'utilisateur n'est exécuté. Le rapport qualité vérifie l'existence des pages, la navigation interne, le balisage de base et l'absence de scripts.

## Utilisation

```python
from papi_core.multi_page_builder import generate_multi_page_project, multi_page_quality_report

result = generate_multi_page_project(
    workspace, "portail",
    {"name": "Portail institutionnel"},
    architecture_brief,
)
report = multi_page_quality_report(workspace, "portail")
```

## Limites à ce stade

Il s'agit d'un générateur statique déterministe, pas d'un agent IA de conception autonome. Les formulaires ne sont pas reliés à un backend, les intégrations métier et l'authentification ne sont pas incluses, et aucun serveur d'aperçu, test navigateur, audit WCAG complet, déploiement ou hébergement n'est fourni. La qualité « entreprise » reste un objectif à démontrer par des tests automatisés et une recette réelle.
