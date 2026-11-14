# Consommation atomique des approbations et reçus — Mission 42

## Problème traité
Mission 41 validait l'approbation Ed25519 en consommant le nonce dans une base SQLite séparée, puis inscrivait le reçu dans le registre. Une panne entre ces deux opérations pouvait consommer le nonce sans créer le reçu.

## Nouveau flux
1. Vérifier la signature Ed25519, le statut de la clé, l'identité propriétaire, le scope, la fenêtre temporelle, le digest et la destination sans consommer le nonce.
2. Ouvrir une transaction SQLite immédiate sur la base du registre.
3. Nettoyer les nonces expirés, puis insérer le nonce courant.
4. Inscrire le reçu et toutes les références d'événements, ou reconnaître le digest déjà enregistré.
5. Valider la transaction une seule fois.

Le nonce et le reçu sont désormais validés ou annulés ensemble dans cette base locale. Les contraintes uniques bloquent les rejeux, les collisions d'événements, les collisions de ressources et les identifiants d'approbation déjà utilisés.

## API
`commit_approved_sync_receipt(...)` dans `runtime/papi_core/sync_atomic_receipt.py`.

La fonction renvoie explicitement `nonce_consumed_atomically`, `receipt_committed`, `import_performed=False` et `execution_enabled=False`.

## Tests
Les tests couvrent le commit, le rejeu, l'idempotence avec une nouvelle approbation, le conflit d'événement, le conflit de ressource et la destination erronée. Les cas de conflit vérifient que le nonce et toutes les lignes sont annulés.

## Limites
Cette atomicité est locale à un seul fichier SQLite et une seule installation. Elle ne fournit pas de registre distribué ni de convergence entre instances. Le paquet ne contient que des références et empreintes, pas les contenus de mémoire ou de messages : aucun import métier n'est possible à cette étape. Aucun transport, worker, scheduler, déploiement ou appel Supabase distant n'est activé.
