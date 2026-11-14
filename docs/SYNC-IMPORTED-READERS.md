# Lecteurs mémoire et PAPI CHAT — contenus importés

## Fonctionnement
Mission 47 connecte les API de lecture existantes au magasin SQLite local de Mission 46, sans modifier les journaux JSONL historiques.

- `search_memory(..., import_db=Path(...))` lit les événements mémoire partagés importés.
- `read_messages(..., import_db=Path(...))` lit les messages PAPI CHAT importés, avec le même filtrage par destinataire que les messages locaux.
- Sans `import_db`, le comportement historique reste inchangé.

## Contrôles de provenance
Le lecteur ouvre SQLite en mode strictement lecture seule. Il n'affiche que les enregistrements reliés à un lot d'import, à un reçu dont le statut est `verified_pending_manual_import` et à une référence de reçu correspondante (event ID, type, record ID et digest). Le digest SHA-256 du JSON canonique est recalculé à chaque lecture.

Chaque événement mémoire est revalidé avec le validateur mémoire et doit rester `remember`, `shared`, `normal`, hors catégorie `decision`. Les messages passent par le validateur PAPI CHAT et le registre d'agents. Les identifiants en double ou collisions entre source locale et importée font échouer la lecture plutôt que choisir silencieusement une version.

## Exemple d'utilisation dans le runtime
```python
from pathlib import Path
from papi_core.memory import search_memory
from papi_core.chat import read_messages

memories = search_memory(
    principal=authenticated_principal,
    query="validation",
    import_db=Path("data/sync-imports.sqlite3"),
)

messages = read_messages(
    recipient="agent-a",
    import_db=Path("data/sync-imports.sqlite3"),
)
```

Le paramètre `principal` de la mémoire reste une identité agent authentifiée ; une simple chaîne d'identifiant ne suffit pas.

## Limites
L'adaptateur n'écrit jamais dans SQLite et ne modifie pas les fichiers JSONL. Les fonctions d'écriture/archivage n'utilisent pas encore le magasin importé. Il n'y a pas de réplication automatique, transport réseau, fusion, résolution de conflits, worker ni scheduler. Le magasin doit être fourni explicitement par le code appelant ; il n'est pas activé implicitement au niveau global.
