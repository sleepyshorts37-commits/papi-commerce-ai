# Mission 121 — Registre gouverné des fournisseurs d'images

## Fonctionnalités
- Catalogue des candidats Cloudflare Workers AI, Pollinations et Hugging Face ZeroGPU.
- Séparation entre présence au catalogue et activation réelle.
- Modèles autorisés explicitement par compte, coût estimé, revue des droits commerciaux et revue de politique de sortie.
- Sélection du modèle le moins coûteux en unités estimées uniquement si une preuve récente, liée au compte et au modèle, couvre toute la campagne.
- Refus fermé si aucun modèle n'est éligible ; aucun endpoint payant ou inconnu n'est utilisé en secours.

## Limites connues
Le catalogue ne constitue pas une mesure en direct de la disponibilité ou des conditions commerciales. Les modèles restent désactivés par défaut. Les coûts/quotas changent et doivent être vérifiés à la source officielle avant activation. L'attestation opérateur ne remplace pas les réservations du ledger transactionnel Cloudflare/Supabase à chaque image.

## Tests
Tests unitaires hors réseau : activation explicite, preuve fraîche, compte correspondant, budget zéro, refus d'un modèle désactivé, doublons et fournisseur inconnu.
