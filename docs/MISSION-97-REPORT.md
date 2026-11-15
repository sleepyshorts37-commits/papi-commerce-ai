# Mission 97 — Porte qualité de la planche personnages PKP-0001
Date : 2026-11-15
Base : Mission 96, commit `68603c39f113f560a1f951798408f6a2d65708f8`

## Objectif
Obtenir une planche modèle stable pour Nia, Bako, Tali et Awa avant toute production en série des illustrations du livre.

## Test visuel réalisé
Une planche de référence a été générée avec les quatre personnages en vues multiples. Elle est consultable dans le rendu image de cette conversation. Le fichier image est disponible dans l'espace de travail de cette session sous `/mnt/data/a_clean_character_sheet_illustration_on_a_light_cr.png`, mais n'a pas été ajouté au dépôt Git ; aucun chemin Git ou URL durable n'est revendiqué.

## Contrôle de fidélité
- Nia : tunique ocre, short bleu nuit, carnet bleu-vert et petites tresses présents ; les variantes de coiffure et les ornements de tunique ne sont pas suffisamment verrouillés entre les vues.
- Bako : haut vert, short brun et sac rouge brique présents ; des poches cargo et des détails de vêtement ont été ajoutés alors qu'ils ne sont pas spécifiés.
- Tali : tortue olive et carapace ovale visibles ; le modèle de cinq grandes plaques et surtout l'encoche arrière droite ne sont pas démontrés avec assez de précision.
- Awa : foulard et tenue indigo cohérents dans l'ensemble ; les vues sont exploitables comme indication générale, pas comme modèle final approuvé.
- Aucun personnage supplémentaire distinct n'a été ajouté ; les répétitions sont des vues de turnaround.

## Décision qualité
**PROVISIONAL / NOT APPROVED.** La planche donne une première direction de proportions et de palette, mais échoue au verrouillage des détails invariants. Elle ne doit pas servir de référence finale pour générer les 24 pages.

## Correctif
Le prompt V2 resserre les vêtements simples, supprime les vignettes d'expressions contradictoires, exige exactement cinq grandes plaques sur la carapace de Tali et demande que l'encoche arrière droite soit clairement visible. Il est consigné dans `publishing/papi-kids/PKP-0001/character-sheet-prompt-v2.md`.

## État de production après Mission 97
- Planches personnages générées : 1.
- Planches personnages approuvées : 0.
- Couverture approuvée : 0.
- Illustrations intérieures finales : 0/24.
- Maquette / PDF : non produits.
- Aucun fichier image ajouté au dépôt.
- Aucun agent activé, aucune publication, dépense ou action externe.
- Aucune CI exécutée/confirmée dans cette mission.

## Étape suivante
Réaliser une nouvelle planche avec le prompt V2 et ne verrouiller les personnages qu'après contrôle explicite des cinq critères. Une fois la planche validée, produire une seule illustration intérieure test (page 1) avant toute série.
