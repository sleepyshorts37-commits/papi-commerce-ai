# Mission 145 — Rapport consolidé de préparation à Amazon KDP

## Livrable
- Assemble les données du package imprimable, les métadonnées, droits, illustrations, spécifications papier, compte, prix et autorisation du propriétaire.
- Exige une attestation distincte d'inspection humaine pour le PDF intérieur et la couverture (identité, date, preuve).
- Ne marque le préflight comme réussi que si ces trois éléments sont présents et valides.
- Réexécute le release gate existant sur les vrais fichiers du stockage privé, leurs empreintes et leur pagination.
- Persiste le rapport JSON avec permissions privées et écriture atomique.

## Gouvernance
- Le meilleur statut est \`ready_for_manual_submission\`, jamais une publication automatique.
- Aucun champ inconnu n'est inventé ; les données absentes restent des blocages.
- Aucun appel externe, aucune dépense, aucun upload ou publication.
