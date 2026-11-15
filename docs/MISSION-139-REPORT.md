# Mission 139 — Générateur PDF intérieur et préflight KDP

## Référentiel KDP vérifié
Source officielle consultée le 15 novembre 2026 :
- https://kdp.amazon.com/help/topic/G201857950
- Toutes les images doivent atteindre au moins 300 DPI ; limite de fichier 650 Mio.
- Minimum 24 pages ; standard color minimum 72 pages ; premium color minimum 24 pages.
- Pour un intérieur avec fond perdu : PDF de coupe + 0,125 po en largeur et + 0,25 po en hauteur.
- Pour 24 à 150 pages : gouttière 0,375 po ; marge extérieure 0,375 po avec bleed et 0,25 po sans bleed.
- Couverture couleur : dos = pagination × 0,002347 po ; fond perdu couverture 0,125 po sur chaque bord ; pas de texte sur le dos jusqu'à 79 pages.

## Livrables
- Validateur de format de coupe, couleur, pagination, marges et bleed sur une table de formats KDP vérifiée.
- Calculateur de dimensions de couverture avec avertissement obligatoire de télécharger et suivre le gabarit KDP exact.
- Générateur ReportLab de PDF intérieur page par page : images approuvées uniquement, SHA-256, dimensions réelles, seuil DPI configurable (300 par défaut), police TrueType incorporée, texte éditable rendu dans les zones spécifiées.
- Vérification du nombre de pages, de l'ordre, des marges, du contenu des zones, du format PDF et de la taille maximale.
- Tests sur 24 pages, calcul de dos, refus du mode standard color à 24 pages, refus des marges insuffisantes et refus d'images non approuvées.

## Blocages de PKP-0001
Le format de coupe, le mode couleur, les marges finales, la pagination imprimée totale, les textes/positions validés et les 24 illustrations ne sont pas encore approuvés. Le PDF final n'a donc pas été généré.
Pour un album couleur de 24 pages, la table officielle indique que le mode standard color commence à 72 pages ; premium color est le seul mode couleur de cette pagination.
Aucune soumission KDP, dépense ou publication n'est effectuée.
