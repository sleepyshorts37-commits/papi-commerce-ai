# Mission 147 — Audit de résolution imprimée

## Livrables
- Calcul du DPI réel source et du DPI pixel final pour chaque image.
- Calcul des pixels minimums KDP à 300 DPI, fond perdu inclus.
- Un simple agrandissement Lanczos n'est jamais considéré comme restauration du détail.
- Une super-résolution IA ou retouche manuelle peut être acceptée uniquement après revue humaine datée, liée au SHA-256 exact de l'image finale.
- Audit de campagne : pages manquantes, pages bloquées et progression imprimable.
- Tests sur les dimensions FLUX 1024×1024, le format 8,5×8,5, le bleed et la validation d'upscaling.

## Constat PKP-0001
Pour une page 8,5×8,5 po sans bleed, KDP exige au moins 2 550×2 550 pixels à 300 DPI. Une sortie FLUX 1 024×1 024 représente environ 120,47 DPI : elle ne peut pas être déclarée prête à imprimer. L'export EPUB peut rester envisageable, mais le paperback attend un procédé de super-résolution validé.
