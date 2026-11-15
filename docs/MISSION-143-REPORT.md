# Mission 143 — Assemblage atomique du dossier imprimable KDP

## Livrable
- Service backend hors réseau qui appelle les deux générateurs : PDF intérieur et PDF couverture.
- Construit les deux fichiers dans un dossier privé temporaire, puis publie le dossier de fabrication atomiquement seulement si les deux rendus réussissent.
- En cas d'échec du second rendu, suppression du staging : aucun package partiel n'est conservé.
- Manifeste JSON avec chemins privés relatifs, SHA-256, pagination, empreinte du gabarit et états de préflight.
- Les préflights restent en attente d'inspection visuelle humaine ; aucune génération de package ne déclare le livre prêt KDP.
- Plafond de dépense zéro ; aucun upload, aucune publication, aucun fournisseur ou service externe.

## Limites
Le service est une fonction backend et n'est pas encore monté dans le serveur applicatif. Le vrai gabarit KDP, les images finales approuvées et les paramètres d'impression PKP-0001 sont toujours requis.
