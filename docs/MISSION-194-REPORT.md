# Mission 194 — Lecture bornée et JSON strict du journal d'audit

## Objectif

Réduire le risque de consommation mémoire incontrôlée lors de la lecture du journal JSONL local, tout en refusant les constantes non standard du JSON.

## Changements

- Limite le journal à 32 Mio avant lecture et relit au maximum cette limite plus un octet.
- Vérifie la taille du fichier après lecture pour détecter un changement de taille pendant l'opération.
- Limite le nombre d'événements à 50 000.
- Limite chaque ligne brute à 64 Kio plus un délimiteur LF ou CRLF.
- Refuse explicitement `NaN`, `Infinity` et `-Infinity` via `parse_constant`.
- Ajoute quatre tests : journal trop grand, ligne brute trop grande, constantes non standard et nombre d'événements excessif.
- Met à jour la documentation et la roadmap.

## Validation

- Tests locaux : non exécutés (environnement de session sans checkout Python local du dépôt).
- CI GitHub Actions : en attente du déclenchement sur cette PR.
- Les tests préexistants de Mission 193 sont validés sur le SHA `9de039051aa44bb3a79c34de706450e6c715719a` (228 tests, workflows core/registry/docs réussis). Le SHA de tête documentaire `b15bf612299ef44ba9da2168cf449093968d0b1c` n'a pas de nouveau run, selon le rapport PR.

## Limites

- Le journal dépassant les limites est refusé; aucune rotation ni archivage automatique n'est ajoutée.
- Les limites sont des garde-fous locaux, pas une politique de conservation ou de sauvegarde.
- Un changement de contenu de même taille par un processus externe ne peut pas être exclu par la seule comparaison de taille; l'intégrité de la chaîne est toujours vérifiée, et le verrou protège les écrivains coopératifs.

## Gouvernance

- PR brouillon empilée sur Mission 193 (#370).
- Aucun changement sur `main`, aucune fusion ou déploiement.
- Aucun worker, agent, scheduler, compte externe, secret, fournisseur ou dépense activé/utilisé.
