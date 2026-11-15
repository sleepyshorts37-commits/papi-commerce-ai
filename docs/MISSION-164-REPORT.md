# Mission 164 — Précision du contrôle de sécurité jeunesse

## Correctifs
- Les règles d'entrée dans l'eau, de consommation d'eau et de manipulation d'objets dangereux exigent désormais un sujet enfant explicite et une action associée.
- Ajout des principales conjugaisons françaises (ex. ramassent, buvons, descendent).
- Reconnaissance des négations \`ne ... pas\`, \`ne ... jamais\`, \`n'y ... pas\` pour ne pas signaler à tort des consignes de prudence.
- Détection des formulations au pluriel pour les enfants sans surveillance.
- Tests des actions réellement dangereuses et des consignes négatives.

## Résultat sur PKP-0001 V2
Le test de sécurité exécute maintenant l'analyse sur le manuscrit V2 du dépôt : 24 pages, zéro alerte lexicale après prise en compte des négations. Cela ne vaut pas approbation de sécurité : la relecture humaine reste obligatoire, notamment pour le contexte, les illustrations et les éléments culturels/scientifiques.
