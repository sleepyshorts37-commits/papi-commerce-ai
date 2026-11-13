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


## Nouvelle cible produit : qualité agence / grande entreprise

Le MVP déterministe décrit ci-dessus n'est pas le produit final et ne satisfait pas le standard attendu. La cible est un studio de création web professionnel capable de concevoir des sites et applications adaptés au besoin, du site institutionnel multi-pages à la plateforme métier ou e-commerce.

La qualité visuelle doit être personnalisée par projet : direction artistique, design system, typographie, grilles, composants, iconographie, responsive multi-écrans et parcours utilisateur. La qualité technique doit inclure une architecture adaptée, des fonctionnalités réellement connectées, une gestion correcte des erreurs, la sécurité, le SEO, l'accessibilité, les performances, les tests et la documentation.

### Portes de sortie obligatoires

Chaque livraison doit disposer d'un dossier de preuves comprenant :
- matrice exigences → pages/fonctionnalités → tests ;
- capture ou rapport de revue visuelle sur plusieurs tailles d'écran ;
- résultats des builds, tests unitaires, intégration et parcours navigateur ;
- contrôles d'accessibilité avec cible WCAG 2.2 AA, écarts documentés et validation humaine ;
- mesures de performance et Core Web Vitals sur environnement de test ;
- rapport sécurité et dépendances, secrets absents du code livré ;
- liste des intégrations réellement actives, simulées ou non configurées ;
- défauts connus, documentation, sources et procédure de transfert.

Les critères de performance et de couverture seront calibrés selon le type de site et son niveau de criticité. Aucun score Lighthouse ou résultat automatisé ne sera considéré comme preuve suffisante à lui seul.

### Paliers de maturité

1. Prototype : maquette ou démonstrateur, jamais présenté comme production.
2. MVP : périmètre limité, fonctions réelles et limites explicites.
3. Production professionnelle : tests, sécurité, performance, accessibilité, exploitation et transfert validés.
4. Entreprise / critique : exigences de résilience, observabilité, sauvegarde/restauration, gouvernance des accès, audit indépendant et continuité adaptées au risque.

Le niveau annoncé doit correspondre aux preuves. Le MVP actuel reste au palier de socle technique expérimental. Il ne produit pas encore de sites de niveau entreprise.

### Chantiers structurants à réaliser

- Moteur de spécification IA et orchestration de génération multi-fichiers.
- Système de design et bibliothèque de composants professionnels.
- Architecture multi-pages et choix de stack par cas d'usage.
- Environnements isolés de prévisualisation et tests navigateur.
- Génération frontend et backend avec contrats d'API, validation et tests.
- Pipelines qualité : accessibilité, SEO, performance, sécurité, responsive et régression visuelle.
- Versionnement, reprise après erreur, audit et export complet.
- Intégrations de production optionnelles, isolées et autorisées.

Aucune connexion payante, aucun déploiement ni aucune publication n'est autorisé par cette spécification seule.

## Itération suivante — direction artistique professionnelle

Le rendu minimal a été remplacé par une première composition éditoriale premium : en-tête de marque, hero, appel à l'action, bande de confiance, contact et pied de page. Le CSS utilise des variables de design tokens, une hiérarchie typographique fluide, des points de rupture tablette/mobile, un focus clavier visible, une navigation d'évitement et la préférence de réduction des animations.

Cette évolution améliore le socle visuel, mais ne prouve pas un niveau entreprise. Le générateur produit toujours une page statique depuis quatre champs de brief. Il ne dispose pas encore d'un sitemap multi-pages, d'un moteur IA, d'un backend, d'un navigateur de prévisualisation, de tests Playwright, de mesures Core Web Vitals ou d'un audit WCAG complet.

### Portes de sortie entreprise

1. Découverte métier et matrice exigences / pages / fonctionnalités / tests.
2. Direction artistique spécifique à la marque, design system et bibliothèque de composants.
3. Architecture multi-pages et choix de stack motivé par le cas d'usage.
4. Responsive testé sur navigateurs et tailles cibles, parcours clavier et lecteurs d'écran.
5. Tests unitaires, intégration, navigateur et régression visuelle.
6. Audit WCAG 2.2 AA, SEO, Core Web Vitals, sécurité et dépendances.
7. Documentation, code source, inventaire des intégrations, limites et procédure de transfert.

Paliers de maturité : Prototype, MVP, Production professionnelle, Entreprise/critique. Le niveau annoncé devra correspondre à des preuves vérifiables et à une validation humaine. Aucun fournisseur payant, hébergement, DNS ou publication n'est activé.
