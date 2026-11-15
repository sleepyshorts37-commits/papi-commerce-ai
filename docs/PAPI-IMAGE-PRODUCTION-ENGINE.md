# Mission 113 — Moteur d'exécution de production d'images

## Livrable
`runtime/papi_core/image_production_engine.py` relie les lots produits par `image_factory`, l'adaptateur de génération parallèle et le centre local d'assets.

## Cycle d'exécution
1. Lire chaque clé d'idempotence dans le centre d'assets.
2. Écarter les images déjà enregistrées : aucune requête fournisseur ni nouvelle consommation de quota.
3. Envoyer uniquement les pages manquantes à `generate_many`, qui applique sa concurrence bornée et ses réservations de quota individuelles.
4. Corréler strictement chaque résultat avec sa clé.
5. Sauvegarder les octets PNG/JPEG/WebP par le centre d'assets, qui vérifie le format, le MIME, la taille et l'empreinte.
6. Retourner un bilan exploitable par statut ; la revue visuelle reste humaine.

## Reprise et sécurité
- Relancer le même lot saute les assets déjà persistés.
- Les erreurs par image n'annulent pas les réussites des autres pages.
- Aucun retry automatique.
- Un résultat fournisseur non corrélé, une réponse sans octets ou un échec de persistance est marqué incertain ; rapprocher le quota et le résultat avant toute nouvelle tentative.
- Le moteur ne déclenche aucun fournisseur à l'initialisation. L'exécution est explicite.
- Aucun fallback payant, secret, worker permanent ou publication KDP.

## Mesures de débit
Le rapport donne le nombre de soumissions fournisseur et les images persistées/ignorées/échouées. Le débit réel en images/heure doit être calculé à partir d'horodatages d'exécution réels ; aucun chiffre synthétique n'est présenté comme une mesure de production.

## Validation
Tests avec générateur simulé et stockage temporaire : persistance, reprise sans nouvel appel, isolation des erreurs et rejet des résultats non corrélés. Aucun appel Cloudflare réel.
