# Migration contrôlée des journaux JSONL vers SQLite

Mission 49 fournit une migration locale, explicite et non destructive des journaux mémoire et PAPI CHAT.

## Préconditions

- Arrêter les processus qui écrivent dans les journaux concernés.
- Vérifier qu'une sauvegarde indépendante existe et choisir un répertoire de sauvegarde protégé.
- Conserver les fichiers sources JSONL inchangés.
- Exécuter la migration pour un seul journal à la fois, puis contrôler le rapport et les comptes.

## Commandes

Depuis la racine du dépôt :

```bash
PYTHONPATH=runtime python -m papi_core migrate-jsonl --kind memory --source data/memory/events.jsonl --database data/local-journals.sqlite3 --backup-dir backups/mission-49 --agents data/agents.json
PYTHONPATH=runtime python -m papi_core migrate-jsonl --kind message --source data/chat/messages.jsonl --database data/local-journals.sqlite3 --backup-dir backups/mission-49 --agents data/agents.json
```

La seconde commande ne doit être exécutée que si le fichier PAPI CHAT existe et après validation du premier rapport.

## Garanties

- Validation complète du journal avant toute insertion.
- Limite de 50 Mio par fichier source.
- Sauvegarde sans écrasement, permissions restrictives et vérification SHA-256.
- Transaction SQLite unique pour tous les enregistrements et le marqueur de migration.
- Rejet des doublons, identifiants incomplets, collisions et journaux invalides.
- Rejouer exactement le même fichier (même type, chemin et SHA-256) renvoie `already_migrated` sans dupliquer les enregistrements.
- Les fichiers JSONL source ne sont ni supprimés ni modifiés.
- En cas d'erreur pendant l'insertion, la transaction entière est annulée ; la sauvegarde vérifiée est conservée.

## Bascule

La migration n'active pas automatiquement SQLite dans l'application. Après vérification manuelle des rapports, des comptes, des empreintes et des sauvegardes, l'opérateur doit configurer explicitement `sqlite_db` sur les opérations mémoire/chat. Maintenir le journal JSONL en lecture/archivage tant que la période de contrôle n'est pas terminée.

Ne pas exécuter les deux modes d'écriture en parallèle pour la même instance sans procédure dédiée. Ne pas supprimer les sources ni les sauvegardes sur la seule base du statut `migrated`.

## Limites

Migration locale uniquement, mono-instance, base non chiffrée au repos. Pas de transport réseau, de migration Supabase, de déploiement, de worker ou de scheduler.
