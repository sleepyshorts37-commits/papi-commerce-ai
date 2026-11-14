# Mission 35 — Procédure opérateur

1. Modifier le registre canonique `data/agents.json` dans une PR dédiée.
2. Conserver les IDs existants lors d'une modification de fonction ou de nom, sauf décision explicite de migration d'identité.
3. Ne jamais réutiliser un ID ou résoudre un homonyme par simple ajout d'un suffixe au nom sans arbitrage.
4. Mettre à jour `docs/ORGANISATION.md` dans la même PR.
5. Exécuter `PYTHONPATH=runtime python -m papi_core organization-check`.
6. Exécuter `PYTHONPATH=runtime python -m papi_core validate` et l'ensemble des tests.
7. Faire approuver tout changement d'identité, de hiérarchie ou de permission par le propriétaire.
8. Ne pas confondre statut planifié et agent déployé.

Le validateur est local et statique. Il ne crée aucun agent, compte, accès ou connexion.
