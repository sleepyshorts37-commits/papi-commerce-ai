# Mission 160 — Verrou KDP multi-format

## Livrable
- Le release gate accepte désormais un indicateur explicite \`ebook_required\`.
- Si l'ebook est demandé, contrôle du chemin privé, SHA-256, ZIP, XML, OPF fixed-layout, mimetype, nombre de pages et pop-ups Kindle.
- Exige un préflight EPUB marqué passé et une attestation humaine Kindle Previewer (réviseur, date, preuve, empreinte SHA-256 exacte de l'EPUB).
- L'attestation d'une version précédente ne peut pas approuver un fichier EPUB modifié.
- Le mode ebook est optionnel pour les projets papier uniquement.
- Publication automatique toujours désactivée.

## Tests
- Ebook demandé sans inspection Kindle Previewer : bloqué.
- Ebook structurellement valide avec preuve Previewer liée au hash : prêt pour soumission manuelle.
- Preuve Previewer d'un hash différent : bloquée.
