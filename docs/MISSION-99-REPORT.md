# Mission 99 — Validation isolée du modèle de Tali
Date : 2026-11-15
Base : Mission 98, commit `f4be0ff45ea4f164e80d827e6b11c670430028a3`

## Objectif
Verrouiller le modèle graphique de Tali indépendamment des autres personnages, en particulier les cinq grandes plaques de la carapace et la petite encoche arrière droite.

## Test graphique réalisé
Une planche isolée a été générée avec trois vues (face, profil, arrière trois-quarts). Le fichier est présent dans l'espace de travail de cette session sous `/mnt/data/a_clean_bright_cream_ivory_background_character.png`. Il n'a pas été ajouté au dépôt Git ; aucun lien durable dans le dépôt n'est revendiqué.

## Contrôle qualité
- Identité : tortue olive, yeux bruns, silhouette amicale — conforme dans l'ensemble.
- Carapace : les grandes plaques sont plus lisibles que dans les essais précédents, mais la séparation et le compte exact des cinq plaques ne sont pas suffisamment incontestables dans les trois vues.
- Encoche : visible sur la vue arrière, mais elle est trop profonde et ressemble à une cavité ou à une partie manquante plutôt qu'à une petite encoche naturelle.
- Cohérence : les trois vues montrent un modèle proche, mais le détail de carapace n'est pas encore verrouillé.

## Décision
**REJECT — modèle non approuvé.** Cette planche ne doit pas devenir la référence de Tali et ne doit pas être utilisée pour générer les illustrations intérieures.

## Correctif consigné
Le prompt V4 réduit explicitement l'encoche à une petite irrégularité peu profonde du contour, interdit tout trou/cavité et renforce le contrôle des cinq plaques principales. Fichier : `publishing/papi-kids/PKP-0001/tali-model-prompt-v4.md`.

## État de fabrication
- Planches personnages complètes générées : 2.
- Tests isolés de Tali : 1.
- Modèle de Tali approuvé : 0.
- Couverture approuvée : 0.
- Illustrations intérieures finales : 0/24.
- Maquette / PDF : non produits.
- Aucun visuel de cette mission versionné dans Git.
- Aucune publication, dépense, activation d'agent ou action externe.
