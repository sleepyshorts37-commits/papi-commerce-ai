# Mission 128 — Verrou de préparation du dossier KDP

## Fonction
Crée une archive candidate contenant l'intérieur PDF, la couverture PDF et un manifeste SHA-256 seulement si les validations humaines, les droits commerciaux, les 24 validations d'illustrations, les métadonnées et le préflight sont présents.

## Gouvernance
Le résultat est \`candidate_ready_for_owner_review\`, pas un fichier autorisé à être téléversé. Aucun appel à Amazon KDP n'est effectué. La publication demeure bloquée jusqu'à une autorisation distincte et explicite du propriétaire.

## Limite
Cette fonction ne crée pas les PDF. Elle attend les fichiers produits par les moteurs de mise en page et inspectés par le préflight.
