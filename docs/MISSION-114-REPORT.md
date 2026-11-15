# Rapport — Mission 114

- **Objectif :** maximiser le nombre d'images réalisables avec les modèles gratuits confirmés et mesurer le débit réel.
- **Code :** `runtime/papi_core/image_model_router.py`.
- **Routage :** registre explicite, sélection du modèle au coût estimé le plus bas, rejet des modèles non confirmés gratuits, aucun fallback payant.
- **Mesure :** images réussies/heure sur durée réellement écoulée, erreurs et modèle sélectionné.
- **Tests :** sélection du modèle économique, refus du modèle non confirmé, rejet des clés dupliquées, formule de débit.
- **Limites :** aucune performance de production mesurée sans compte et appels réels autorisés ; coûts à confirmer par modèle.
- **Statut :** PR brouillon soumise à CI.
