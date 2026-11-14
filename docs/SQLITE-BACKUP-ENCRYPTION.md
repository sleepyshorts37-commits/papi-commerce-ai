# Chiffrement et gestion des clés des sauvegardes SQLite

Mission 51 ajoute le chiffrement authentifié AES-256-GCM aux snapshots SQLite locaux de la Mission 50.

## Générer une clé

```bash
PYTHONPATH=runtime python -m papi_core sqlite-keygen --key-file "$HOME/.config/papi/keys/backup-2026.key"
```

La clé contient 32 octets aléatoires, créée en mode exclusif et avec permissions 0600 sur POSIX. Le programme n'affiche jamais la valeur de la clé. Le fichier de clé doit rester hors du dépôt Git, hors du dossier des sauvegardes et hors des répertoires synchronisés non approuvés. Conserver une copie protégée dans un gestionnaire de secrets ou un coffre chiffré indépendant ; perdre la clé rend les sauvegardes irrécupérables.

## Chiffrer un snapshot

```bash
PYTHONPATH=runtime python -m papi_core sqlite-backup-encrypt --backup backups/sqlite/sqlite-<SHA256>.sqlite3 --key-file "$HOME/.config/papi/keys/backup-2026.key" --manifest backups/encrypted/backup-2026.manifest.json
```

Produit un fichier `.enc` et un manifeste. Le contenu utilise AES-256-GCM avec nonce aléatoire de 96 bits et AAD qui lie la version, l'algorithme, l'identifiant de clé, le nom du fichier et le nonce. L'authentification GCM détecte toute modification du contenu ou de ces champs. La taille est limitée à 256 Mio pour cette implémentation en mémoire ; les fichiers plus grands sont refusés, jamais tronqués. Le snapshot source n'est pas modifié.

## Vérifier sans écrire de base en clair à l'emplacement utilisateur

```bash
PYTHONPATH=runtime python -m papi_core sqlite-backup-verify-encrypted --manifest backups/encrypted/backup-2026.manifest.json --key-file "$HOME/.config/papi/keys/backup-2026.key"
```

Authentifie le ciphertext, déchiffre dans un fichier temporaire local aux permissions restrictives et exécute `PRAGMA integrity_check`. Le fichier temporaire est supprimé après contrôle. L'espace temporaire doit être protégé ; pour un risque élevé, utiliser un volume chiffré.

## Déchiffrer vers un nouveau chemin

```bash
PYTHONPATH=runtime python -m papi_core sqlite-backup-decrypt --manifest backups/encrypted/backup-2026.manifest.json --key-file "$HOME/.config/papi/keys/backup-2026.key" --destination data/recovered.sqlite3
```

Le déchiffrement exige l'authentification GCM et le contrôle SQLite avant publication. La destination doit être absente ; aucun écrasement n'est autorisé. Le fichier résultant est en clair : le stocker sur un volume chiffré et limiter ses permissions.

## Rotation de clé

1. Générer une nouvelle clé dans un fichier différent avec `sqlite-keygen`.
2. Ré-encrypter la sauvegarde vers un nouveau manifeste :

```bash
PYTHONPATH=runtime python -m papi_core sqlite-backup-rotate-key --manifest backups/encrypted/backup-2026.manifest.json --old-key-file "$HOME/.config/papi/keys/backup-2026.key" --new-key-file "$HOME/.config/papi/keys/backup-2027.key" --new-manifest backups/encrypted/backup-2027.manifest.json
```

3. Vérifier le nouveau manifeste avec la nouvelle clé.
4. Garder l'ancienne clé et les anciens fichiers jusqu'à validation de la nouvelle sauvegarde et de la politique de rétention.
5. Révoquer/détruire l'ancienne clé uniquement après validation des sauvegardes de remplacement et selon une procédure humaine documentée.

La rotation ré-encrypte un snapshot vers de nouveaux fichiers ; elle ne détruit ni l'ancienne clé ni l'ancien ciphertext.

## Gestion et limites de sécurité

- Ne jamais committer une clé, la copier dans un ticket, un journal, une variable visible ou une PR.
- Une clé locale en fichier 0600 n'est pas un HSM ni un gestionnaire central de secrets ; le chiffrement du disque et les sauvegardes de la clé restent essentiels.
- AES-GCM authentifie le contenu ; SHA-256 du ciphertext sert au contrôle préalable de corruption.
- Les tailles au-delà de 256 Mio sont refusées par cette version.
- Aucun stockage distant, aucune clé dans GitHub Actions, aucun déploiement, worker, scheduler ou traitement des données réelles.
