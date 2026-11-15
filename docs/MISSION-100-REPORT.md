# Mission 100 — Nouvelle validation graphique de Tali
Date : 2026-11-15
Base : Mission 99, commit `713ddecc770b13cc112e384f248c9b80219313c0`

## Objectif
Appliquer le prompt V4 et décider si Tali peut être verrouillée comme personnage avant de commencer les illustrations intérieures.

## Deux tests générés
Deux nouveaux tests visuels ont été produits pendant cette mission.
- Test A : le générateur a transformé la demande en fiche de personnage avec titre, caractéristiques, expressions, palette, repère de taille et une scène avec un enfant. La carapace comporte de nombreuses plaques/subdivisions et l'encoche demandée n'est pas correctement représentée.
- Test B : nouvelle fiche de turnaround avec titre, sous-titres, légendes, expressions et panneau de caractéristiques non demandés. La carapace présente une mosaïque de plusieurs écailles, pas cinq grandes plaques simples. Aucune encoche arrière droite conforme n'est identifiable.

Les deux images sont donc **REJECT**. Elles ne sont pas ajoutées au dépôt Git.

## Décision
**Tali non verrouillée.** Ne pas produire les 24 illustrations, ne pas approuver de couverture et ne pas utiliser ces images comme références de continuité.

## Correctif
Le prompt V5 isole uniquement la géométrie de la carapace vue du dessus, sans personnage, afin de réduire les détails que le générateur invente. Fichier : `publishing/papi-kids/PKP-0001/tali-shell-study-prompt-v5.md`.

## État cumulé après Mission 100
- Planches complètes : 2.
- Tests isolés / études Tali : 3.
- Images générées pendant Mission 100 : 2, rejetées.
- Modèle de Tali approuvé : 0.
- Couverture approuvée : 0.
- Illustrations intérieures finales : 0/24.
- Maquette / PDF : non produits.
- Aucun fichier image ajouté au dépôt Git.
- Aucun agent activé, aucune publication, dépense ou action externe.
