# PAPI WEB BUILDER — MVP technique sûr

## Mission exécutée

Le dépôt contient maintenant un premier moteur déterministe de génération de sites statiques. Il s'agit d'un socle technique local, pas encore d'un agent IA autonome.

Module : `runtime/papi_core/website_builder.py`

Tests : `tests/test_website_builder.py`

## Capacités implémentées

- Création d'un projet statique isolé dans un répertoire de travail choisi.
- Génération de `index.html`, `styles.css` et `project.json`.
- Échappement HTML des contenus utilisateur.
- Validation stricte des champs et limites de taille.
- Identifiant projet limité à un slug sûr ; rejet des chemins traversants.
- Refus d'écraser un projet existant.
- Modifications itératives limitées aux champs du brief autorisés.
- Rapport de contrôle reproductible : doctype, langue, viewport, feuille CSS locale, absence de balise script, taille et CSS présent.
- Export ZIP limité aux trois fichiers autorisés.
- Métadonnées de prévisualisation de type `static_file_only` ; aucune publication.

## Limites explicites

Ce MVP ne comprend pas :
- de compréhension de prompt par modèle IA ;
- de fournisseur LLM ou clé API ;
- de serveur de prévisualisation, navigateur intégré ou environnement d'exécution ;
- de framework JavaScript, composants arbitraires, génération de backend ou base de données ;
- de test navigateur réel, Lighthouse, audit WCAG complet ou test responsive automatisé sur plusieurs moteurs ;
- d'intégration WhatsApp, e-mail, paiement, CRM ou carte ;
- d'hébergement, DNS, domaine ou publication.

Les modifications sont structurées (champs connus) et non des instructions libres. Le rendu est un modèle HTML/CSS simple. Les fonctions de génération et d'export sont des bibliothèques locales ; aucun processus externe, commande shell ou appel réseau n'est lancé.

## Utilisation locale

Depuis la racine du dépôt :

```python
from papi_core.website_builder import (
    generate_project, update_project, quality_report, export_project
)

brief = {
    "name": "Pharmacie Baobab",
    "tagline": "Votre santé, notre priorité",
    "description": "Présentation de la pharmacie.",
    "contact": "Mbour — contact à confirmer",
}
generate_project("./workspace", "pharmacie-baobab", brief)
update_project("./workspace", "pharmacie-baobab", {"tagline": "Une nouvelle accroche"})
report = quality_report("./workspace", "pharmacie-baobab")
if report["passed"]:
    export_project("./workspace", "pharmacie-baobab", "./exports/pharmacie-baobab.zip")
```

Tests ciblés :

```bash
PYTHONPATH=runtime python -m unittest tests.test_website_builder -v
```

## Garde-fous

- Le code source exporté est statique et n'embarque aucune clé ou configuration secrète.
- Le contenu fourni par l'utilisateur est échappé avant insertion HTML.
- Les noms de fichiers sont une liste blanche fixe.
- L'export refuse les destinations situées dans le projet.
- Le rapport ne constitue pas une homologation de sécurité ou une recette client.
- Le code n'expose aucune route de publication. Toute future intégration d'hébergement/DNS nécessitera un contrôle d'accès et une autorisation distincts.

## Suite nécessaire

1. Ajouter un vrai aperçu isolé sans exécution arbitraire.
2. Ajouter validation responsive et tests navigateur.
3. Définir les contrats d'interface pour un fournisseur IA, avec adaptateur simulé par défaut et secrets hors dépôt.
4. Mettre en place une politique de quotas, limites de fichiers, journalisation et nettoyage des espaces projets.
5. Faire une revue sécurité indépendante avant tout pilote réel.
