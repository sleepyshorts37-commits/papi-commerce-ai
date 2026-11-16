# Mission 184 — PAPI CONNECT ADAPTERS

## Objectif
Relier le catalogue de la Mission 183 à une interface d'adaptateurs commune, sans intégrer de service distant ni engager de coût.

## Réutilisation
Le dépôt disposait déjà de `papi_core.providers` et de `MockGenerationProvider` pour les générations texte/image. Cette mission réutilise ce contrat plutôt que de créer une seconde implémentation concurrente.

## Nouveautés
- `papi_core.connectors.ConnectorGateway` : passerelle entre catalogue, permissions d'agent et adaptateurs.
- `local.mock` : entrée locale explicitement activée dans le catalogue, coût maximal 0 XOF, sans secret et sans réseau.
- `tests/test_connectors.py` : tests de simulation, permissions, fournisseur inconnu, candidat sans adaptateur, blocage des fournisseurs externes et plafond de coût.

## Sécurité
- Les fournisseurs externes restent bloqués, même si leurs entrées figurent au catalogue.
- Le fournisseur doit exister, être activé, déclarer la capacité demandée et exiger des permissions détenues par l'agent.
- Les opérations dépassant le plafond fournisseur sont refusées avant exécution.
- La simulation renvoie un contenu explicitement marqué comme simulation ; ce n'est pas une vraie image ni un texte final.
- Aucun secret, compte, service distant, abonnement ou déploiement n'est ajouté.

## Test
`PYTHONPATH=runtime python -m unittest discover -s tests -v`
