# Registre des migrations Supabase

Le fichier `manifest.json` est l'inventaire versionné des migrations du dépôt. Il décrit leur ordre, leurs fichiers up/down, leur politique de rollback et leur statut de dépôt. Le statut `repository_only_not_applied` signifie explicitement qu'aucune application sur une base distante n'est revendiquée.

## Validation hors ligne

Depuis la racine du dépôt :

```bash
python scripts/validate_migration_manifest.py
python -m unittest tests.test_migration_manifest
```

Le validateur vérifie les noms, l'ordre, l'unicité des versions, la présence des deux côtés up/down, l'absence de fichiers SQL de migration non enregistrés et calcule les empreintes SHA-256. Il ne se connecte à aucune base et n'exécute aucun SQL.

## Procédure avant toute application future

1. Examiner le SQL up et down et les impacts sur les données.
2. Vérifier l'empreinte SHA-256 et l'ordre de version.
3. Obtenir l'approbation explicite du propriétaire et une fenêtre de maintenance.
4. Sauvegarder et tester une restauration avant migration.
5. Appliquer une migration à la fois dans un environnement isolé.
6. Enregistrer version, checksum, environnement, horodatage, résultat et approbateur dans un ledger d'exécution externe protégé.
7. Ne jamais déduire qu'une migration a été appliquée depuis sa seule présence dans Git.

## Limites

Ce registre est un inventaire statique et un validateur local. Il n'est pas un exécuteur, ne prouve pas l'état d'une base distante, ne remplace pas un ledger transactionnel et n'autorise aucune migration de production. Le ledger d'exécution réel reste à concevoir et à valider séparément.
