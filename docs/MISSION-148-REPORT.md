# Mission 148 — Provenance de résolution jusqu'au PDF et à la publication

## Livrables
- Migration PostgreSQL 016 : dimensions source, méthode d'agrandissement et identité/date/SHA de revue de super-résolution.
- Stockage privé conserve la résolution native d'origine en plus des dimensions finales.
- Registre et lecteur de statut PostgreSQL exposent source/final et preuve de revue.
- Validation humaine d'une illustration AI super-resolution/manual retouch enregistre aussi la revue de résolution liée au SHA final.
- Tableau de bord iPhone affiche les dimensions source → finales et le statut de revue.
- Le générateur PDF intérieur recalcule le DPI source et final ; il refuse une image simplement agrandie par Lanczos.
- Le verrou de publication exige un DPI pixel final suffisant et, si la source est sous 300 DPI, une super-résolution/retouche approuvée par un humain et liée à l'empreinte exacte.
- CI applique la migration 016 et vérifie le backfill des assets existants.

## Effet concret
Une illustration 1024×1024 étirée à 2550×2550 ne passe plus le contrôle d'impression. Elle ne peut passer qu'après un vrai traitement de super-résolution ou une retouche manuelle, puis une revue humaine documentée. La taille en pixels seule ne suffit pas.
