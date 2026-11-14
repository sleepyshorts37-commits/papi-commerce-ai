# Approbation cryptographique des paquets — Mission 40

## Contrat
Une attestation Ed25519 du propriétaire autorise uniquement un paquet exact pour une destination exacte. Le payload signé lie :
- le scope fixe `papi.sync_bundle.import` et la décision `approved`;
- le digest SHA-256 canonique du paquet;
- les identités source et destination et l'identifiant d'export;
- la liste ordonnée des identifiants d'événements;
- un identifiant d'approbation et une fenêtre temporelle bornée.

La vérification utilise le registre public Ed25519 existant et son anti-rejeu SQLite local. La clé privée reste dans le stockage local protégé; aucune clé ni secret n'est commité.

## Refus par défaut
Signature invalide, propriétaire différent, destination inattendue, digest modifié, ordre ou liste d'événements modifié, scope non autorisé, approbation expirée/future ou TTL excessif entraînent un refus.

## Limites
- L'anti-rejeu SQLite est local à une installation et ne constitue pas un registre distribué.
- Le contrôle ne consomme pas l'approbation dans le ledger SQL partagé.
- Aucun import, transport, écriture métier, worker ou synchronisation multi-instance n'est activé.
- Une signature prouve le contrôle de la clé privée enregistrée, pas la légitimité juridique du titulaire.
- L'approbation cryptographique n'est pas une autorisation d'exécuter automatiquement l'import.

## Exploitation
Provisionner/rotater/révoquer les clés via les procédures Ed25519 déjà documentées. Garder la clé privée hors dépôt, sauvegarder le registre public, contrôler l'horloge et traiter tout refus comme bloquant. Toute future consommation devra être atomique, durable et liée au digest exact avant un import transactionnel.
