# Mission 159 — Package EPUB 3 fixed-layout et préflight structurel

## Livrable
- Enveloppe de production EPUB autour du générateur fixed-layout existant.
- Build dans un staging privé, validation ZIP/XML, ordre et compression mimetype, OPF pre-paginated, navigation, XHTML par page, pop-ups Kindle et intégrité.
- Manifeste privé avec SHA-256, nombre de pages et état de préflight.
- Renommage atomique uniquement si le package est complet ; rollback en cas d'échec.
- Le statut reste en attente de Kindle Previewer ; aucune sortie n'est déclarée prête à téléverser.

## Limites
Le vrai EPUB PKP-0001 attend toujours les illustrations approuvées, la couverture numérique, le nom d'auteur confirmé et les positions de texte validées. Kindle Previewer doit contrôler le rendu sur les appareils ciblés.
