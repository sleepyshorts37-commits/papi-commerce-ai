# Mission 171 — Package multi-format broché + ebook

## Livrable
- Étend l'orchestrateur de package broché pour inclure un EPUB 3 fixed-layout optionnel ou requis.
- Produit PDF intérieur, couverture full-wrap et EPUB dans le même répertoire staging privé.
- Vérifie que pagination, texte de chaque page, titre et auteur concordent entre les formats.
- Vérifie les illustrations ebook approuvées et la couverture numérique approuvée.
- Valide la structure EPUB (ZIP/XML, OPF, navigation, pages et pop-ups Kindle).
- Écrit un manifeste commun avec SHA-256, chemins, pages, préflight et statut ebook.
- Renommage atomique unique ; si l'EPUB échoue, aucun PDF partiel n'est publié.
- Ebook en attente de Kindle Previewer ; PDFs en attente d'inspection manuelle.

## Gouvernance
L'ebook reste optionnel si non demandé. Aucun upload KDP, aucune publication, aucun fournisseur image ou dépense.
