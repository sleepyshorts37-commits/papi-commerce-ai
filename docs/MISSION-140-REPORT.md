# Mission 140 — Verrou final de publication KDP

## Livrable
Un moteur de release gate vérifie avant toute soumission :
- métadonnées éditoriales définitives (titre, auteur, langue, description, mots-clés) ;
- validation éditoriale humaine datée ;
- droits commerciaux et preuve documentaire ;
- illustration approuvée et résolution 300 DPI pour chaque page ;
- PDF intérieur et couverture présents, SHA-256, nombre de pages et préflight ;
- format, papier, mode couleur et empreinte du gabarit KDP officiel ;
- éligibilité du compte, versement et fiscalité vérifiés ;
- prix, coût d'impression et redevance datés ;
- autorisation explicite du propriétaire ;
- plafond de dépense égal à zéro.

## Gouvernance
Le résultat le plus favorable est \`ready_for_manual_submission\`. Le moteur conserve \`publication_execution_enabled=false\` : il ne téléverse pas et ne publie rien. Une action de publication nécessitera un flux distinct, une confirmation explicite et les permissions correspondantes.

## Validation
Tests couvrant dossier incomplet, dossier complet, illustration non approuvée, absence d'autorisation et intégrité SHA-256.
