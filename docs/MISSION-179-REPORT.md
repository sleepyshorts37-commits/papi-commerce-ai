# Mission 179 — Dossier ZIP de soumission manuelle KDP

## Livrable
- Export ZIP en mémoire uniquement après autorisation propriétaire liée au dernier manifeste.
- Revalide la preuve d'autorisation en base, les revues hash-bound, la sécurité jeunesse, les droits commerciaux et le plafond zéro.
- Recalcule les SHA-256 des fichiers privés et refuse les chemins traversants, liens symboliques et fichiers modifiés.
- Le ZIP contient PDF intérieur, couverture, EPUB si présent, manifeste, métadonnées KDP normalisées, attestations, README manuel et SHA256SUMS.
- Aucun secret ni chemin privé absolu n'est exporté ; aucun fichier ZIP n'est conservé sur le serveur.
- Aucun appel externe, téléversement KDP ou publication.

## Usage
Le propriétaire télécharge le ZIP depuis l'iPhone, contrôle les fichiers, puis effectue lui-même la soumission sur Amazon KDP.
