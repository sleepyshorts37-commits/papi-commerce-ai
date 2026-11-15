# Mission 146 — Génération Cloudflare sous verrou gratuit et zéro dépense

## Référentiel Cloudflare officiel vérifié le 15 novembre 2026
- Workers AI Free : 10 000 Neurons par jour, remise à zéro à 00:00 UTC.
- Sur Workers Free, le dépassement provoque un échec ; le passage à Workers Paid est requis pour dépasser le quota. Workers Paid commence à 5 USD/mois et facture l'excédent à 0,011 USD / 1 000 Neurons.
- Modèle : \`@cf/black-forest-labs/flux-1-schnell\`, réponse image JPEG encodée en Base64.
- Tarification du modèle : 4,8 Neurons par tuile 512×512 + 9,6 Neurons par étape.
- Pour 1024×1024 et 4 étapes : 57,6 Neurons/image ; 24 images : 1 382,4 Neurons estimés (13,8 % du quota quotidien).
Sources :
- https://developers.cloudflare.com/workers-ai/platform/pricing
- https://developers.cloudflare.com/workers-ai/models/flux-1-schnell
- https://developers.cloudflare.com/changelog/post/2026-07-28-models-require-workers-paid

## Livrables
- Client Cloudflare limité à un seul modèle FLUX.1 schnell ; aucune route de secours.
- Exécution bloquée sans autorisation explicite, compte Workers Free, quota frais, preuve de disponibilité du modèle, licence commerciale confirmée et plafond dépense zéro.
- Estimation Neurons par taille et nombre d'étapes.
- Réservation/consommation dans un ledger PostgreSQL partagé et transactionnel, idempotence de la demande et coût monétaire forcé à zéro.
- Les erreurs HTTP, quotas épuisés et réponses invalides ne déclenchent aucun upgrade ni fallback payant.
- Tests avec transport simulé uniquement ; aucun appel Cloudflare réel.

## Limite essentielle
La preuve de quota reste une attestation opérateur issue du tableau de bord Cloudflare ; l'API ne permet pas ici de confirmer indépendamment toute la consommation du compte. Il faut un compte Workers Free dédié ou tenir compte des usages externes avant chaque campagne.
Le modèle renvoie 1024×1024 dans ce contrat. Ce format convient à l'EPUB fixe, mais ne satisfait pas à lui seul les 300 DPI d'un livre imprimé 8,5×8,5 po. Un processus d'agrandissement haute qualité et une QA imprimée sont requis ; aucune illustration n'a été générée dans cette mission.
