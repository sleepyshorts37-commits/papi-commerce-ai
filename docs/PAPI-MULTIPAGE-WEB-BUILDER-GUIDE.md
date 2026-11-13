# Guide — générateur multi-pages PAPI

Le module `papi_core.multipage_site` expose `generate_multipage_site(workspace, slug, brief)`.

Exemple de brief :
```python
brief = {
  "brand": "Hôtel Baobab",
  "sector": "hotel",
  "audience": "voyageurs",
  "tone": "professional",
  "pages": [
    {"slug": "accueil", "title": "Bienvenue", "summary": "Présentation de l'hôtel.",
     "facts": ["Établissement situé à Saly"]},
    {"slug": "chambres", "title": "Nos chambres", "summary": "Présentation des chambres.",
     "facts": ["Chambres climatisées", "Wi-Fi disponible"]}
  ]
}
result = generate_multipage_site("./workspace", "hotel-baobab", brief)
```

Le site produit `index.html`, `pages/*.html`, `styles.css` et `project.json`. Chaque page reçoit son contenu validé à partir des faits fournis. Le générateur accepte de 2 à 6 pages. Chaque résumé doit faire au maximum 180 caractères et chaque page accepte au maximum 7 faits (le résumé est lui aussi contrôlé comme un fait commercial). Les identifiants invalides ou dupliqués sont refusés et un projet existant n'est jamais écrasé.

La génération est locale et déterministe. Aucun hébergement, publication, contact client ou transaction n'est déclenché. Relecture humaine obligatoire.
