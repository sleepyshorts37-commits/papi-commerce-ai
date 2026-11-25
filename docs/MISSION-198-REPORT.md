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
- Tests locaux non exécutés. CI GitHub réussie sur le SHA `d55ea1c6585faddc290cf36e935096ce2f82a6c9` : 248 tests Python (`Ran 248 tests`, `OK), validation des registres et contrôles documentaires réussis. `pip check` ne signale aucune dépendance cassée ; les deux audits `pip-audit` ne trouvent aucune vulnérabilité connue dans les graphes analysés. PostgreSQL 16 jetable : schéma, migrations, concurrence des claims et rollback réussis. Le contrôle Supabase Preview est ignoré, aucune preview distante n'étant associée à la branche.

## Vérifications GitHub Actions
- [PAPI core tests — run #2864](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45579915186) : succès, 248 tests.
- [PAPI registry validation — run #924](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45579915045) : succès.
- [PAPI documentation checks — run #891](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45579915200) : succès.
- [Supabase Preview](https://github.com/sleepyshorts37-commits/papi-commerce-ai/runs/139087009958) : ignoré, aucune preview associée à la branche.

## Gouvernance
PR brouillon empilée sur Mission 197 (#374). Aucun changement sur `main`, aucune fusion, aucun déploiement, aucune connexion fournisseur, aucun secret, paiement, contact externe ou activation d'agent/worker.
