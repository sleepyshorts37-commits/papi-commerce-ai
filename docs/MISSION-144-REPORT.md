# Mission 144 — Vérification structurelle du gabarit KDP officiel

## Correctif
- Le générateur de couverture lit désormais le PDF de gabarit avec pypdf.
- Exige un PDF valide, non chiffré et d'une seule page.
- Compare la MediaBox réelle du PDF aux dimensions de la géométrie fournie, tolérance 0,5 point.
- La géométrie doit toujours être liée à l'empreinte SHA-256 du gabarit exact.
- Les tests utilisent maintenant de vrais PDF d'une page créés avec ReportLab et vérifient le refus d'un gabarit modifié.

## Limite de sécurité
La vérification prouve l'intégrité du fichier, le nombre de pages et les dimensions globales. Elle ne prouve pas que les coordonnées des panneaux, du dos, du code-barres ou des zones de sécurité ont été correctement extraites du dessin technique du gabarit. Cette extraction et son contrôle visuel restent obligatoires.
