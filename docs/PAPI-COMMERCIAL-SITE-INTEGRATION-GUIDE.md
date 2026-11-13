# Guide — sites commerciaux générés par PAPI

## Utilisation
Depuis la racine du dépôt, avec `PYTHONPATH=runtime`, appeler `generate_commercial_site(workspace, slug, brief)` depuis Python.

Le brief reprend les champs du générateur commercial : `content_type`, `sector`, `brand`, `offer`, `facts`, et éventuellement `audience`, `tone`, `cta`.

Exemple de structure :
```python
brief = {
    "content_type": "business_page",
    "sector": "hotel",
    "brand": "Hôtel Baobab",
    "offer": "Séjour en bord de mer",
    "facts": ["Établissement situé à Saly", "Restaurant sur place"],
    "cta": "Contactez la réception pour confirmer les disponibilités.",
}
result = generate_commercial_site("./workspace", "hotel-baobab", brief)
```

## Résultat
Le dossier de projet contient `index.html`, `styles.css` et `project.json`. Le résultat comprend le brouillon commercial et le rapport qualité. Les sites ne sont pas publiés.

## Limites et sécurité
- Le générateur est déterministe et local ; ce n'est pas une génération par LLM.
- Seuls les faits du brief sont utilisés.
- La sortie doit être relue et validée par un humain.
- Les allégations non vérifiées et les dosages pharmaceutiques sont refusés.
- Les contenus de plus de 1 000 caractères sont rejetés, sans troncature.
- Aucun hébergement, réseau, contact client, paiement ou publication n'est déclenché.
