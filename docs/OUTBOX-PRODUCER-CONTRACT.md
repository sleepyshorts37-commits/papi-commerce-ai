# Contrat producteur PAPI OUTBOX

## Règle d'atomicité

Toute mutation métier et son intention outbox doivent être exécutées dans la même transaction PostgreSQL, sur la même connexion. Ne jamais effectuer un commit métier puis appeler l'outbox via une seconde requête HTTP : une panne entre les deux créerait un événement manquant.

Exemple de séquence SQL (les noms de tables/champs métier sont illustratifs et doivent être adaptés au domaine réel) :

```sql
begin;

update public.papi_tasks
   set task = jsonb_set(task, '{status}', '"confirmed"'::jsonb),
       version = version + 1,
       updated_at = now()
 where id = 'TASK-ORDER-123';

-- Le backend doit vérifier qu'une seule ligne métier a été modifiée.
select public.papi_enqueue_outbox(
    'order-confirmed:ORDER-123:v1',
    'order.confirmed',
    'ORDER-123',
    '{"order_ref":"ORDER-123","version":1}'::jsonb,
    5
);

commit;
```

En production, le producteur doit contrôler le nombre de lignes modifiées et lever une erreur si la mutation attendue n'a pas eu lieu ; cette erreur doit annuler la transaction complète.

## Contenu autorisé

Le payload est un objet JSON de 16 KiB maximum. Il doit contenir uniquement des références techniques et les données minimales nécessaires au consommateur. Interdits : mots de passe, clés API, tokens, OTP, PIN, CVV, numéros de carte/compte, corps de conversation et données personnelles non nécessaires.

## Déduplication

- Clé identique + event_type, aggregate_id, payload et max_attempts identiques : le même UUID est retourné.
- Clé identique avec une intention différente : conflit dur ; le producteur doit enquêter, pas changer silencieusement la clé.
- La clé est conservée à travers les reprises et doit être transmise au destinataire lorsque celui-ci propose une API idempotente.

## Livraison

Le claim ne signifie pas que l'événement est livré. Le worker externe futur devra appeler le fournisseur, puis ack seulement après une réponse vérifiée. En cas de timeout ambigu, consulter l'API de statut du fournisseur ou utiliser sa clé idempotente. Sans coopération du fournisseur, un doublon externe demeure possible.

## Limites actuelles

Cette mission crée le registre et les primitives de file. Elle n'intègre aucune table métier réelle, ne crée aucun worker actif et ne contacte aucun fournisseur. L'intégration spécifique se fera lorsque le domaine (commande, notification, paiement, etc.) et ses frontières transactionnelles seront définis.
