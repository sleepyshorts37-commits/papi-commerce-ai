# Réception locale authentifiée des paquets sync

## Objectif
La Mission 44 relie le spool .papisync (Mission 43) à la vérification Ed25519 et au reçu atomique nonce + références (Mission 42). Elle fournit une seule entrée locale fail-closed pour recevoir un paquet sur son instance cible.

## Chaîne de réception
1. Lire le fichier avec read_sync_package : JSON canonique, taille, nom, empreinte, structure et approbation liée au paquet sont contrôlés.
2. Vérifier la signature Ed25519, le propriétaire autorisé, la portée, la fenêtre de validité, le digest, la liste ordonnée des événements et la destination exacte.
3. Dans une transaction SQLite BEGIN IMMEDIATE, consommer le nonce et enregistrer le reçu et ses références.
4. Retourner un rapport sans exposer de clé ou de contenu.

Le fichier source est conservé. Un paquet déjà reçu avec une nouvelle approbation valide est idempotent; le nouveau nonce est consommé et aucun deuxième reçu n'est créé. Un rejeu ou une collision échoue sans commit partiel.

## Commande
```bash
PYTHONPATH=runtime python -m papi_core receive-sync-package \
  --package ./incoming/paquet.papisync \
  --owner-id OWNER_ID \
  --registry ./keys/public.json \
  --ledger ./data/sync-receipts.sqlite3 \
  --destination INSTANCE_ID
```

Les chemins et identifiants sont des paramètres locaux à renseigner par l'opérateur. Le registre public de clés doit être provisionné par un canal de confiance. La clé privée ne doit jamais être copiée sur l'instance destinataire ni dans le dépôt.

## Garanties
- Authentification Ed25519 et vérification de portée/destination avant inscription.
- Anti-rejeu et reçu/références atomiques dans le même SQLite local.
- Conservation du fichier .papisync d'origine.
- Pas de contenu mémoire/chat dans le paquet ni dans le reçu.
- Pas d'import, d'exécution d'agent, de transport réseau ou de suppression automatique du fichier.

## Limites
Le registre de nonces et reçus est mono-instance local. Aucun import métier n'est implémenté; les événements restent des références et empreintes. Aucun transport réseau, réplication, stockage distribué, worker, scheduler, déploiement ou test multi-instance réel n'est inclus. Une signature prouve le contrôle de la clé publique enregistrée, pas à elle seule l'identité juridique du propriétaire.
