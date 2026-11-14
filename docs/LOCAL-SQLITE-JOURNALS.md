# Journaux SQLite locaux — mémoire et PAPI CHAT

Mission 48 introduit un mode d'écriture SQLite local, explicite et facultatif, pour la mémoire et PAPI CHAT.

## Utilisation

Les fonctions existantes conservent leur comportement JSONL par défaut. Pour choisir SQLite, l'appelant passe le même chemin de base locale aux fonctions concernées :

- `remember_fact(..., sqlite_db=Path("data/local-journals.sqlite3"))`
- `supersede_memory(..., sqlite_db=Path("data/local-journals.sqlite3"))`
- `search_memory(..., sqlite_db=Path("data/local-journals.sqlite3"))`
- `send_message(..., sqlite_db=Path("data/local-journals.sqlite3"))`
- `read_messages(..., sqlite_db=Path("data/local-journals.sqlite3"))`

Sans `sqlite_db`, les journaux JSONL historiques restent utilisés. Les imports synchronisés restent une source de lecture séparée, via `import_db`.

## Garanties

- Insertions transactionnelles `BEGIN IMMEDIATE`, identifiants uniques et contraintes SQL.
- Tables protégées contre UPDATE et DELETE par triggers append-only.
- Fichier SQLite créé en permissions 0600 et dossier en 0700 lorsque créé par le module.
- Rejet des liens symboliques et des chemins qui ne sont pas des fichiers.
- Les lecteurs vérifient les enregistrements et conservent les validations métier et contrôles d'accès existants.
- Déduplication exacte entre JSONL et SQLite ; collisions divergentes refusées.
- Aucune communication réseau, aucun service distant, aucun worker ou scheduler activé.

## Migration progressive

Il n'y a aucune migration automatique des journaux JSONL. Le mode SQLite est opt-in par appelant. Pour basculer un environnement, sauvegarder les journaux, effectuer une migration contrôlée et vérifier les comptes/empreintes avant de configurer l'application pour passer `sqlite_db`. Ne pas faire pointer simultanément des processus concurrents vers des modes d'écriture différents sans procédure de bascule et de déduplication.

## Limites

- La base est locale, non chiffrée au repos et mono-instance.
- Aucun verrou interprocessus n'est ajouté aux journaux JSONL historiques.
- Pas de réplication, de synchronisation réseau, de sauvegarde distante ou de restauration automatique.
- Les lecteurs peuvent combiner JSONL local, SQLite opérationnel et import SQLite explicite ; les conflits sont refusés.
- La création de tables et triggers se fait localement au premier enregistrement, jamais sur Supabase.
