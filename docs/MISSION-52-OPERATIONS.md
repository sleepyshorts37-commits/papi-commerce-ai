# Mission 52 — Procédure opérationnelle

## Vérification d'une sauvegarde v2
Utiliser la commande existante :

```bash
PYTHONPATH=runtime python -m papi_core sqlite-backup-verify-encrypted --manifest backups/encrypted/backup.manifest.json --key-file "$HOME/.config/papi/keys/backup.key"
```

## Compatibilité
Les manifestes v1 valides restent lisibles. Les nouvelles opérations de chiffrement produisent le format v2. Aucun fichier historique n'est modifié.

## Réponse à une altération
En cas de rejet du manifeste, ne pas tenter de corriger manuellement les champs, de contourner l'authentification ou d'écraser les artefacts. Restaurer une copie connue et validée du manifeste et du ciphertext depuis une sauvegarde protégée.

## Limites
Le lecteur vérifie l'authenticité des champs couverts par l'AAD et l'intégrité du ciphertext. La disponibilité et la confidentialité de la clé restent sous la responsabilité de l'opérateur. Aucune clé n'est stockée dans GitHub ni dans un service distant.
