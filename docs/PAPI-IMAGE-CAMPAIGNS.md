# Mission 115 — Campagnes multi-livres et production d'images reprenable

## Objectif
Orchestrer la production d'illustrations de plusieurs livres dans une campagne unique, avec lots bornés, reprise idempotente et arrêt contrôlé en cas de résultat incertain.

## Modules
- `runtime/papi_core/image_campaign.py` : planification multi-livres et exécution bornée.
- `tests/test_image_campaign.py` : tests déterministes et sans réseau.

## Planification
`plan_image_campaign(...)` :
- accepte une série de livres et leurs pages ;
- rejette les identifiants de livres dupliqués et les limites dépassées ;
- réutilise le planificateur de lots existant par livre ;
- calcule le volume total de pages et les unités estimées ;
- ne déclenche aucun appel fournisseur.

## Exécution et reprise
`execute_image_campaign(...)` :
- limite le nombre de lots exécutés par invocation ;
- peut être rappelé avec le même plan : les assets déjà persistés sont ignorés par le moteur d'exécution ;
- retourne l'index du prochain lot et un bilan par lot ;
- s'arrête dès qu'un lot comporte un échec ou un résultat incertain ;
- retourne les identifiants de lots à conserver dans un checkpoint externe via `blocked_batch_ids`, pour éviter leur resoumission aveugle ;
- aucun retry automatique, aucun worker ni ordonnanceur permanent.

Le plan est déterministe, mais la persistance de l'état de campagne entre instances nécessite un stockage de checkpoint durable fourni par l'application. Le module ne prétend pas rendre le système serverless durable à lui seul.

## Sécurité et limites
- Le modèle doit figurer dans le registre de coûts explicitement autorisés.
- Les quotas restent réservés par l'adaptateur fournisseur avant chaque appel.
- Aucun fallback payant.
- Aucune publication de livre, aucun achat et aucun déploiement.
- Les images générées restent soumises à une revue visuelle humaine.

## Validation
Tests unitaires avec générateur et stockage simulés ; aucun appel Cloudflare réel.
