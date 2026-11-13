# Architecture multi-pages — PAPI WEB BUILDER

## Livrable

- Module : `runtime/papi_core/site_architecture.py`
- Tests : `tests/test_site_architecture.py`
- Fonction : `build_site_architecture(brief)`

Le contrat accepte un nom de projet, un inventaire de pages et un inventaire d'exigences métier. Il produit un sitemap déterministe avec routes et chemins de fichiers normalisés, puis une matrice de traçabilité exigence → pages.

## Règles appliquées

- 1 à 20 pages par brief.
- Page `home` obligatoire.
- Routes limitées à des slugs ASCII sûrs ; aucune route libre ni chemin traversant.
- Identifiants d'exigences uniques et priorités `must`, `should` ou `could`.
- Chaque page référence au moins une exigence connue.
- Chaque exigence doit être couverte par au moins une page.
- Les champs inattendus sont rejetés plutôt que transmis à un moteur d'exécution.

## Exemple

```python
from papi_core.site_architecture import build_site_architecture

architecture = build_site_architecture({
    "project_name": "Portail institutionnel",
    "requirements": [
        {"id": "brand", "description": "Présenter la marque", "priority": "must"},
        {"id": "contact", "description": "Permettre le contact", "priority": "must"},
    ],
    "pages": [
        {"slug": "home", "title": "Accueil", "purpose": "Découverte", "requirements": ["brand"]},
        {"slug": "contact", "title": "Contact", "purpose": "Prise de contact", "requirements": ["contact"]},
    ],
})
```

## Limites

Le résultat est un plan validé, pas un site généré. Il ne crée aucun fichier web, n'exécute aucun code, n'appelle aucun modèle IA et ne publie rien. La prochaine étape consiste à connecter ce contrat au générateur multi-pages, puis à ajouter navigation, tests de liens internes et tests navigateur.
