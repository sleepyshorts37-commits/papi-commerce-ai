# Mission 198 — Publication atomique des fichiers d'archives d'audit

## Date et objectif
25 novembre 2026. Empêcher qu'une interruption pendant l'écriture d'un journal restauré rende visible un fichier final partiel ou bloque une reprise sûre.

## Constat
Le helper précédent ouvrait directement le chemin final avec `O_CREAT | O_EXCL`, puis écrivait les octets. Une interruption du processus pendant l'écriture pouvait laisser un fichier tronqué au chemin de destination. La reprise refusait ensuite d'écraser ce chemin, même si le contenu était incomplet.

## Modifications
- Écrit désormais les octets dans un fichier temporaire privé créé exclusivement dans le même répertoire.
- Gère les écritures partielles et `InterruptedError`.
- Synchronise le fichier temporaire avant publication.
- Publie l'inode complet par lien matériel atomique ; l'opération échoue si la destination existe et ne la remplace jamais.
- Nettoie le temporaire après publication ; un résidu temporaire après arrêt brutal est caché et empêche la validation stricte d'une archive incomplète.
- Ajoute un test qui simule une écriture partielle suivie d'une erreur et vérifie que le chemin final et le fichier de verrouillage ne sont pas créés.
- Met à jour la documentation d'exploitation et la roadmap.

## Limites
- Le système de fichiers doit supporter les liens matériels ; sinon, la publication échoue fermé.
- Un arrêt brutal peut laisser un fichier temporaire caché. Une archive dont le répertoire contient un résidu ne passe pas la vérification exacte de son contenu et nécessite une inspection manuelle.
- La synchronisation du répertoire parent reste effectuée par l'appelant après la vérification finale.
- Aucun stockage distant, réplication, WORM, sauvegarde hors site ou restauration après sinistre n'est validé.
- Tests locaux non exécutés ; CI à confirmer sur le SHA final.

## Gouvernance
PR brouillon empilée sur Mission 197 (#374). Aucun changement sur `main`, aucune fusion, aucun déploiement, aucune connexion fournisseur, aucun secret, paiement, contact externe ou activation d'agent/worker.
