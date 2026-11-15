# Mission 176 — Revue iPhone des PDF/EPUB et verrou de sortie

## Livrable
- Le tableau de bord iPhone affiche le dernier package, les hashes et les états de chaque fichier.
- Téléchargement authentifié des PDF en aperçu et de l'EPUB en pièce jointe, sans exposer les chemins privés.
- Approuver/refuser chaque fichier depuis l'iPhone avec notes obligatoires.
- Le release gate exige une attestation humaine append-only liée à la version et au SHA-256 exacts pour le PDF intérieur, la couverture et, si requis, l'EPUB.
- Les contrôles automatisés sont distingués de la revue humaine ; Kindle Previewer reste une attestation distincte pour l'ebook.
- Tests : package complet avec attestations, revue manquante, hash périmé et UI mobile.

## Gouvernance
Un nouveau package invalide les attestations précédentes par version/hash. Aucun fichier n'est envoyé à KDP ; l'état maximal reste prêt pour soumission manuelle après validation propriétaire.

## Interface et endpoint
- Panneau iPhone avec jeton distinct et liste de blocages.
- Endpoint HTTPS GET en lecture seule ; aucun état modifié.
- Les revues doivent correspondre aux empreintes SHA-256 exactes de la dernière version du package.

## Contrôle final et endpoint iPhone
- Évaluateur fail-closed : vérifie version/empreinte manifeste, empreintes exactes PDF/EPUB, revues humaines, sécurité jeunesse, fiche commerciale et droits.
- Une modification d'empreinte invalide l'approbation précédente.
- Endpoint HTTPS GET en lecture seule protégé par `PAPI_KIDS_RELEASE_GATE_TOKEN`.
- Panneau iPhone affiche l'éligibilité à une confirmation finale et les blocages.
- Le gate n'autorise aucune publication : téléversement KDP désactivé, dépenses zéro.
