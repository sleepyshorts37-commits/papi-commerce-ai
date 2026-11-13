# Guide de correction SEO — PAPI WEB BUILDER

Cet audit analyse des fichiers statiques localement. Il ne contacte aucun moteur de recherche et ne publie rien.

## Erreurs bloquantes
- **Titre absent** : ajouter un élément `<title>` descriptif à chaque page.
- **Description absente** : ajouter `<meta name="description" content="...">`.
- **Langue absente** : préciser la langue principale, par exemple `<html lang="fr">`.
- **Nombre de H1 incorrect** : conserver un seul H1 principal par page et structurer les sous-parties avec H2/H3.
- **Lien interne cassé** : corriger le chemin ou créer la page cible.
- **Lien javascript:** : remplacer par une URL ou une action HTML accessible, sans code exécutable dans l'attribut href.
- **Sitemap XML invalide** : corriger la syntaxe XML et vérifier les URL listées.

## Avertissements
- **Titre hors de 30–60 caractères** et **description hors de 50–160 caractères** : plages indicatives pour la lisibilité des extraits, pas des règles absolues de classement.
- **Canonical absent** : définir une URL canonique uniquement lorsque le domaine public réel est connu. Ne jamais inventer un domaine.
- **Open Graph incomplet** : ajouter `og:title` et `og:description` pour améliorer l'aperçu de partage ; cela ne garantit pas un meilleur classement.
- **robots.txt absent** : ajouter une politique adaptée au site public et y référencer le sitemap avec son URL absolue réelle.
- **noindex détecté** : vérifier que cette directive est intentionnelle avant publication.

## Contrôle humain et limites
Le rapport n'évalue pas la qualité éditoriale, les backlinks, l'indexation réelle, les données structurées avancées, les Core Web Vitals terrain, les règles propres à chaque moteur ou les obligations sectorielles. Il ne remplace pas Search Console ni une revue SEO humaine. Ne pas retirer une directive noindex ou modifier une canonical sans vérifier l'intention du propriétaire.

## Utilisation
Depuis la racine du dépôt, avec le dossier généré dans un espace de travail :
```python
from papi_core.seo_audit import audit_static_site_seo

report = audit_static_site_seo("/chemin/vers/workspace", "slug-du-site")
print(report)
```

Le résultat contient `passed`, `errors`, `warnings`, un diagnostic par page, l'état du sitemap et `published: false`. L'audit est local, en lecture seule, et effectue zéro requête réseau.
