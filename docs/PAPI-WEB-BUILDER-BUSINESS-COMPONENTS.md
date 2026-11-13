# Composants métier statiques — PAPI WEB BUILDER

Le générateur accepte quatre nouveaux types de sections dans `spec.sections[slug]` :

- `product_catalog` : 1 à 12 fiches avec `name`, `description`, `price_label`, `cta_label`, `target_page`.
- `team` : 1 à 12 profils avec `name`, `role`, `bio`.
- `testimonials` : 1 à 8 citations avec `quote`, `author`, `role`. Le rendu affiche explicitement que les témoignages sont fournis par le client et non vérifiés.
- `service_cards` : 1 à 8 cartes avec `title`, `body`.

Tous les champs textuels sont validés et échappés. Les CTA produits ne peuvent pointer que vers une page interne existante. Les URL d'images, HTML, scripts, CSS libre, panier, paiement, réservation réelle et collecte de données ne sont pas pris en charge. Les composants sont de simples présentations statiques ; prix, biographies et témoignages doivent être fournis et vérifiés par le client avant publication.

## Exemple

```python
{
    "sections": {
        "home": [
            {
                "id": "catalogue",
                "type": "product_catalog",
                "eyebrow": "Boutique",
                "heading": "Sélection du moment",
                "body": "Prix indicatifs fournis par le commerçant.",
                "items": [
                    {
                        "name": "Café local",
                        "description": "Paquet de café.",
                        "price_label": "3 000 FCFA",
                        "cta_label": "Nous contacter",
                        "target_page": "contact"
                    }
                ]
            }
        ]
    }
}
```

La présence de ces composants ne constitue ni une boutique transactionnelle ni une intégration de réservation.
