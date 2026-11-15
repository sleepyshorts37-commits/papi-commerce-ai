# Mission 142 — Générateur de couverture complète Amazon KDP

## Livrable
- Génération d'un PDF couverture pleine largeur (quatrième + dos + face avant) en une page.
- Obligatoire : gabarit PDF officiel KDP exact, empreinte SHA-256 et géométrie de panneaux extraite de ce gabarit. Aucun calcul approximatif ne remplace le gabarit.
- Contrôle des panneaux arrière/dos/avant, fond perdu KDP de 0,125 po, zone code-barres laissée blanche.
- Illustrations avant/arrière issues du stockage privé, SHA-256, dimensions et résolution minimale 300 DPI, approbation humaine requise.
- Texte titre/auteur/résumé éditable, police TrueType incorporée et zones vérifiées.
- Refus de texte sur le dos pour les livres de moins de 80 pages ; traitement du dos des livres plus longs laissé en attente d'un gabarit et d'un traitement typographique spécifiques.
- Tests offline : PDF pleine couverture, gabarit modifié, image non approuvée, texte de dos interdit.

## Limites
- Le format final, le papier, le nombre total de pages, l'auteur, le résumé et le gabarit officiel du livre PKP-0001 ne sont pas encore confirmés. Aucun PDF de couverture réel n'a donc été produit.
- La sortie reste un rendu structurel ; l'inspection visuelle et le préflight KDP manuel sont obligatoires.
- Aucun upload KDP, aucun déploiement, aucun appel image/IA, aucune dépense ni publication.
