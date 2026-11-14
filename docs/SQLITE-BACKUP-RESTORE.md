# Sauvegarde, vérification et restauration SQLite locales

Mission 50 ajoute un mécanisme local de snapshot cohérent pour les bases SQLite de PAPI COMMERCE AI.

## Créer une sauvegarde

```bash
PYTHONPATH=runtime python -m papi_core sqlite-backup --database data/local-journals.sqlite3 --backup-dir backups/sqlite
```

La commande utilise l'API de sauvegarde SQLite (snapshot cohérent même si une transaction est en cours), exécute `PRAGMA integrity_check`, puis écrit une copie immuable par convention et un manifeste JSON. Les fichiers sont créés en permissions restrictives (0600) dans un dossier (0700). Le manifeste contient le nom du fichier, sa taille, SHA-256, le résultat d'intégrité et `user_version`. Les sauvegardes existantes ne sont jamais écrasées.

## Vérifier une sauvegarde

```bash
PYTHONPATH=runtime python -m papi_core sqlite-backup-verify --manifest backups/sqlite/sqlite-<SHA256>.manifest.json
```

La vérification refuse les liens symboliques, les chemins de fichier inattendus, les tailles ou empreintes incohérentes et toute base qui échoue à `PRAGMA integrity_check`. Le SHA-256 détecte une altération accidentelle ; il ne constitue pas une signature d'origine contre un attaquant capable de remplacer à la fois la sauvegarde et son manifeste. Conserver les sauvegardes dans un emplacement protégé et séparé.

## Restaurer sans écrasement

```bash
PYTHONPATH=runtime python -m papi_core sqlite-restore --manifest backups/sqlite/sqlite-<SHA256>.manifest.json --destination data/restore-check.sqlite3
```

La restauration valide d'abord le manifeste et la sauvegarde, restaure vers un fichier temporaire dans le dossier cible, vérifie l'intégrité et le `user_version`, puis publie le fichier par création exclusive. **La destination doit être absente** : aucun remplacement, suppression ou écrasement n'est permis. Restaurer d'abord vers un chemin de contrôle distinct, vérifier les données et seulement ensuite planifier une bascule manuelle.

## Contrôles opérationnels

1. Arrêter les processus écrivains avant une sauvegarde de maintenance (le snapshot reste cohérent même en présence d'écritures concurrentes).
2. Conserver au moins une copie sur un support ou emplacement distinct de la machine source.
3. Vérifier le manifeste immédiatement après création et périodiquement.
4. Faire un exercice de restauration vers un chemin neuf et contrôler les journaux mémoire/PAPI CHAT.
5. Protéger les fichiers et le manifeste comme des données sensibles ; SQLite n'est pas chiffré au repos par cette fonction.

## Limites et garde-fous

- Outils locaux uniquement ; aucun envoi cloud, aucune sauvegarde distante ou automatisation planifiée.
- La restauration n'est pas lancée sur les données réelles et ne change pas la base active.
- Le SHA-256 n'est pas une signature numérique et le manifeste doit être conservé de manière fiable.
- Aucun déploiement, worker, scheduler, contact externe, publication ou mouvement financier.
