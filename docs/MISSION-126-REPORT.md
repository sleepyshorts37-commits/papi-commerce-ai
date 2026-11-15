# Mission 126 — Générateur HTML de l'intérieur PKP-0001

## Fonction
Génère un document HTML d'impression de 24 pages à partir du manuscrit, d'une image réelle par page et d'une fiche de placement de texte par page. Les textes restent éditables et sont échappés pour éviter l'injection HTML. Le format de page est fourni explicitement à partir du gabarit KDP choisi.

## Limites
- Ce rendu HTML n'est pas un PDF final et ne remplace pas l'inspection PDF.
- Aucune image n'est fournie à ce jour ; le rendu réel reste bloqué jusqu'à 24 images approuvées.
- Les positions de texte doivent être définies et validées par page.
- Le gabarit KDP officiel et le fond perdu doivent être déterminés avant production.
- Aucun téléversement KDP n'est autorisé.

## Tests
24 pages, insertion d'images en data URI, texte éditable, absence d'assets, zones hors page et échappement HTML.
