# Mission 143 — Export EPUB 3 fixe pour album jeunesse

## Référentiel KDP officiel consulté
- https://kdp.amazon.com/help/topic/GFFHCXVPHRZW8SJ5
- https://kdp.amazon.com/en_US/help/topic/G200634390
- Les albums illustrés peuvent utiliser une mise en page fixe ; EPUB est accepté si conforme aux Kindle Publishing Guidelines.
- Pour les livres enfants, KDP recommande les pop-ups de texte (Region Magnification) lorsque le texte doit pouvoir être agrandi.
- Le package exige une page XHTML par page Kindle, les métadonnées fixed-layout, original-resolution, book-type children, et les ancres app-amzn-magnify avec target/source/ordinal.
- Les polices peuvent être intégrées via @font-face.

## Livrables
- Générateur EPUB 3 fixed-layout, page par page, avec sommaire, couverture, images et police incorporée.
- Text pop-ups de type Region Magnification pour chaque bloc de texte.
- Contrôle des actifs approuvés, SHA-256, dimensions, ratio, positions de pop-up et résolution.
- Archive ZIP EPUB validée (mimetype premier et non compressé, container, OPF, navigation).
- Tests sur 24 pages, refus d'illustrations non approuvées et de zones trop proches des bords.

## Limites
- Aucun EPUB réel PKP-0001 généré : images, textes, typographie et couverture finales absents.
- Kindle Previewer doit encore vérifier le rendu sur appareils cibles.
- Aucun upload KDP, aucune dépense ni publication.
