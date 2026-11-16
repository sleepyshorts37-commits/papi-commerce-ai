# Mission 184 — PAPI CONNECT ADAPTERS

## Objectif
Relier le catalogue de la Mission 183 à une interface d'adaptateurs commune, sans intégrer de service distant ni engager de coût.

## Réutilisation
Le dépôt disposait déjà de `papi_core.providers` et de `MockGenerationProvider` pour les générations texte/image. Cette mission réutilise ce contrat plutôt que de créer une seconde implémentation concurrente.

## Nouveautés
- `papi_core.connectors.ConnectorGateway` : passerelle entre catalogue, permissions d'agent et adaptateurs.
- `local.mock` : entrée locale explicitement activée dans le catalogue, coût maximal 0 XOF, sans secret et sans réseau.
- `tests/test_connectors.py` : tests de simulation, permissions, fournisseur inconnu, candidat sans adaptateur, blocage des fournisseurs externes, plafonds et intégrité des résultats.

## Contrat d'adaptateur renforcé
- L'enregistrement exige un identifiant, un nom et des capacités valides.
- Les adaptateurs externes et les adaptateurs locaux déclarant des credentials sont refusés dans cette mission.
- Les requêtes rejettent les types incorrects, notamment les booléens utilisés comme montants ou limites numériques.
- Chaque résultat est contrôlé : type de retour, fournisseur, capacité, longueur du contenu, SHA-256, coût entier non négatif et indicateur de simulation.
- Le résultat de `local.mock` doit rester marqué comme simulation et conserver son préfixe explicite ; il ne peut pas être présenté comme un livrable final.
- Les erreurs de validation du fournisseur sont normalisées en `ConnectorError` à la frontière de la passerelle.

## Sécurité
- Les fournisseurs externes restent bloqués, même si leurs entrées figurent au catalogue.
- Le fournisseur doit exister, être activé, déclarer la capacité demandée et exiger des permissions détenues par l'agent.
- Les opérations dépassant le plafond fournisseur sont refusées avant exécution ; le coût retourné est vérifié à nouveau après exécution.
- La passerelle ne réalise elle-même aucun appel réseau. Les adaptateurs enregistrés doivent être du code de confiance et faire l'objet d'une revue avant leur ajout.
- La simulation renvoie un contenu explicitement marqué comme simulation ; ce n'est pas une vraie image ni un texte final.
- Aucun secret, compte, service distant, abonnement ou déploiement n'est ajouté.

## Vérification
Commande prévue :
```sh
PYTHONPATH=runtime python -m unittest tests.test_connectors -v
PYTHONPATH=runtime python -m unittest discover -s tests -v
```

Les tests sont ajoutés au dépôt. Leur réussite doit être confirmée par GitHub Actions ; aucune exécution locale n'est revendiquée dans ce rapport.
