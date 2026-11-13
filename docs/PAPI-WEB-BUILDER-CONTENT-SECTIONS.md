# Sections de contenu réutilisables — PAPI WEB BUILDER

## Contrat d'entrée

Le brief de génération accepte maintenant un champ facultatif `sections`, indexé par slug de page. Chaque page peut recevoir au maximum huit sections. Les identifiants de section doivent être uniques dans la page.

Exemple :

```python
spec = {
    "name": "École Horizon",
    "industry": "education",
    "sections": {
        "home": [
            {
                "id": "programmes",
                "type": "feature_grid",
                "eyebrow": "Nos parcours",
                "heading": "Apprendre avec méthode",
                "body": "Des formations adaptées à chaque étape.",
                "items": [
                    {"title": "Fondamentaux", "body": "Construire les bases."},
                    {"title": "Perfectionnement", "body": "Développer son expertise."},
                ],
            },
            {
                "id": "faq",
                "type": "faq",
                "eyebrow": "Besoin d'aide",
                "heading": "Questions fréquentes",
                "body": "Les informations essentielles.",
                "items": [
                    {"question": "Comment s'inscrire ?", "answer": "Contacter le secrétariat."}
                ],
            },
        ]
    },
}
```

## Types autorisés

| Type | Utilisation | Champs spécifiques |
|---|---|---|
| `intro` | Présentation éditoriale | `body` |
| `feature_grid` | Cartes de services ou avantages | `items[{title, body}]` (2 à 6) |
| `stats` | Chiffres clés | `items[{value, label}]` (2 à 4) |
| `faq` | Questions/réponses accessibles | `items[{question, answer}]` (1 à 8) |
| `cta` | Appel à l'action interne | `cta_label`, `target_page` |

## Garde-fous

- Les champs inconnus sont refusés.
- Le HTML fourni par l'utilisateur est toujours traité comme du texte et échappé.
- Aucun script, style, HTML brut, URL arbitraire ou CSS utilisateur n'est accepté.
- Les CTA pointent exclusivement vers un slug de page existant dans le même site.
- Les longueurs, types, listes, identifiants et nombres de sections sont bornés.
- Les sections sont rendues en HTML sémantique ; les composants FAQ utilisent `details/summary`.

## Limites

Le moteur reste un générateur statique déterministe. Les sections ne fournissent pas encore de panier, réservation, authentification, paiement, formulaire relié à un CRM ou données dynamiques. Les contenus, chiffres, témoignages et promesses doivent être validés par le client. Les tests CI et audits navigateur/accessibilité restent obligatoires avant de qualifier un site de livraison professionnelle.
