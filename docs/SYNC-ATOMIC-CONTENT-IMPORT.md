# Import atomique du contenu de synchronisation — Mission 46

## Objet
Importer les enregistrements mémoire partagés et messages PAPI CHAT contenus dans un fichier `.papidata`, uniquement après vérification du paquet `.papisync`, de l'approbation Ed25519, de la destination et de la cohérence des empreintes.

## Transaction et stockage
La commande `import-sync-content` utilise une base SQLite locale. Dans une seule transaction `BEGIN IMMEDIATE`, elle :
1. consomme le nonce de l'approbation (anti-rejeu) ;
2. crée ou vérifie le reçu et ses références ;
3. crée le marqueur de lot d'import ;
4. insère les enregistrements complets mémoire/chat.

Une collision, un rejeu, une divergence de références ou une erreur SQL annule l'ensemble de la transaction. Un bundle déjà importé avec le même digest de contenu est idempotent ; une nouvelle approbation valide consomme son propre nonce sans dupliquer les données.

## Données et limites
Les lignes importées sont conservées dans `sync_imported_records` avec type, ID, digest, JSON canonique et digest du bundle. Les données sources `.papisync` et `.papidata` sont conservées. Les journaux historiques `data/memory/events.jsonl` et `data/chat/messages.jsonl` ne sont pas modifiés : ce magasin SQLite est une zone d'import contrôlée, pas encore un remplacement transparent des lecteurs mémoire/chat.

Les filtres de confidentialité et les restrictions de portée de Mission 45 restent applicables. Les fichiers ne sont pas chiffrés par cette mission ; les permissions locales et la revue humaine restent nécessaires.

## Utilisation locale
```sh
PYTHONPATH=runtime python -m papi_core import-sync-content \
  --package ./incoming/export.papisync \
  --payload ./incoming/export.papidata \
  --owner-id OWNER_ID \
  --registry ./keys/public.json \
  --ledger ./data/sync-imports.sqlite3 \
  --destination INSTANCE_ID \
  --agents ./data/agents.json
```

Le registre d'agents doit être le fichier JSON utilisé localement par le validateur PAPI. Le chemin de base SQLite peut être identique à celui du registre de reçus existant pour conserver une transaction commune.

## Garanties
- signature Ed25519, propriétaire, portée, durée de validité et destination vérifiés ;
- bundle et charge utile vérifiés avant toute écriture ;
- nonce, reçu, références et contenu commités atomiquement dans SQLite ;
- aucune exécution de tâche, aucun message externe, aucune publication ni opération financière ;
- les imports répétés ne dupliquent pas les enregistrements.

## Limites restantes
Pas de transport réseau, chiffrement, fusion des journaux JSONL, résolution automatique de conflits, réplication distribuée, workers, scheduler ou déploiement. Les agents ne consomment pas encore directement les enregistrements de cette zone SQLite. L'import ne signifie donc pas que la synchronisation multi-instance complète est opérationnelle.
