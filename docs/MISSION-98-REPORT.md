# Mission 98 — Deuxième essai de planche personnages PKP-0001
Date : 2026-11-15
Base : Mission 97, commit `8ab6b77213702e391af31750acca3285452f1976`

## Objectif
Tester le prompt V2 et vérifier si les quatre modèles peuvent être stabilisés avant la production des illustrations intérieures.

## Test réalisé
Une seconde planche a été générée avec les quatre personnages, en vues face/profil/dos, sur fond uni. Le fichier image est présent dans l'espace de travail de cette session sous `/mnt/data/a_clean_character_turnaround_sheet_illustration_on.png`. Il n'a pas été ajouté au dépôt Git ; aucun lien durable n'est revendiqué.

## Contrôle
- Nia : tunique ocre simple, short bleu nuit, sandales et carnet bleu-vert visibles. Les vues sont globalement cohérentes.
- Bako : haut vert doux, short brun, sandales et sac rouge brique visibles. La tenue est plus simple que lors du premier essai ; les vues sont globalement cohérentes.
- Awa : foulard indigo, tunique longue et pantalon sobre ; silhouette adulte cohérente.
- Tali : couleur olive et silhouette de tortue cohérentes, mais la carapace comporte des subdivisions supplémentaires et le motif ne respecte pas clairement la règle des cinq grandes plaques. L'encoche arrière droite n'est pas clairement identifiable.

## Décision qualité
**REJECT — 0 planche approuvée.** Le contrôle de Tali échoue à un invariant essentiel. Ne pas utiliser cette image comme référence de production et ne pas lancer les 24 illustrations sur cette base.

## Travail ajouté
Le prompt isolé V3 de Tali est consigné dans `publishing/papi-kids/PKP-0001/tali-model-prompt-v3.md`. La prochaine tentative doit verrouiller la carapace séparément avant de réintégrer Tali dans une planche de groupe.

## État de fabrication
- Planches personnages générées cumulées : 2.
- Planches personnages approuvées : 0.
- Couverture approuvée : 0.
- Illustrations intérieures finales : 0/24.
- Maquette / PDF : non produits.
- Image de cette mission non versionnée dans Git.
- Aucun agent activé, aucune publication, dépense ou action externe.
