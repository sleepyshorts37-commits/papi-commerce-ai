# Rapport — génération de contenus commerciaux PAPI

## Livrables
- runtime/papi_core/content_generation.py : moteur déterministe local.
- tests/test_content_generation.py : tests du contrat, types, secteurs et garde-fous.
- docs/PAPI-CONTENT-GENERATION-GUIDE.md : guide d'utilisation et limites.
- docs/PAPI-CONTENT-GENERATION-5-DAYS.md : plan de cycle.

## Périmètre
Quatre formats : fiche produit, présentation de service, présentation d'établissement et publication commerciale. Cinq secteurs : pharmacie, hôtel, restaurant, commerce de détail et services professionnels.

## Sécurité
Le moteur ne contacte aucun fournisseur IA, ne fait aucune requête réseau, n'exécute aucun code utilisateur et ne publie aucun contenu. Il n'utilise que les faits transmis dans le brief. Les allégations sensibles explicites et dosages pharmaceutiques sont refusés. La revue humaine est obligatoire.

## Validation
Les tests ont été ajoutés. Les résultats CI doivent être vérifiés sur la PR avant validation finale du cycle. Aucun déploiement ou merge n'a été effectué.