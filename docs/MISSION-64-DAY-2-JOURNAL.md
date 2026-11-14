# Mission 64 — Jour 2 : journal durable

Ajout de `runtime/papi_core/rotation_journal.py`. Le journal est créé de manière exclusive, en mode 0600, puis synchronisé avec fsync du fichier et du répertoire. Le contenu lie les états ancien/nouveau de la clé privée et du registre par SHA-256.

Le lecteur contrôle le type de fichier, le nombre de liens, le propriétaire et les permissions. Les états binaires privés ne sont jamais écrits dans les journaux applicatifs ni dans les messages d'erreur.
