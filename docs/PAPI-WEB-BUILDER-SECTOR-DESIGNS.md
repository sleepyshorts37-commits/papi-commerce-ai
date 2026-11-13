# Systèmes de design sectoriels — PAPI WEB BUILDER

## Profils intégrés

Le moteur multi-pages accepte `industry` dans le brief projet. Six profils sont disponibles :

| Clé | Domaine | Direction visuelle |
|---|---|---|
| `corporate` | Entreprise | Éditorial, institutionnel |
| `ecommerce` | Commerce | Palette naturelle et chaude, cartes produit prêtes à spécialiser |
| `hospitality` | Hôtellerie | Ambiance chaleureuse, formes organiques |
| `professional_services` | Services professionnels | Direction sobre, expertise |
| `education` | Éducation | Palette stimulante, sections pédagogiques |
| `health` | Santé | Palette apaisante, présentation centrée sur la confiance |

Chaque profil fournit des couleurs de marque, un vocabulaire d'accroche, un traitement visuel de la zone héro et des sections réutilisables. Le système ajoute des cartes de contenu, des appels à l'action et une composition responsive. Les valeurs sont contrôlées par une liste fermée : aucune règle CSS arbitraire n'est injectée depuis le brief.

## Exemple

```python
generate_multi_page_project(
    workspace,
    "hotel-baobab",
    {
        "name": "Hôtel Baobab",
        "industry": "hospitality",
        "tagline": "L'art de recevoir sur la Petite Côte",
    },
    architecture_brief,
)
```

## Limites et prochaine validation

Les profils constituent des fondations visuelles sectorielles, pas encore des sites métier complets. Le catalogue produits, la réservation, les paiements, les formulaires reliés, les espaces clients et les systèmes de gestion ne sont pas implémentés. Les images de marque réelles et les contenus éditoriaux restent à fournir ou à valider par le client.

Les tests ajoutés couvrent le choix de secteur, les tokens de marque, le rendu multi-pages, l'échappement HTML et le rapport qualité. Ils doivent encore être exécutés dans un environnement Python/CI. Aucun audit visuel navigateur, audit WCAG 2.2 AA complet ou test de performance n'a été effectué.
