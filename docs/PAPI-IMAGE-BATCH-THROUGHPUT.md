# PAPI — Génération d'images en lots et débit contrôlé

## Objectif opérationnel
Augmenter le débit de génération d'images en exécutant plusieurs requêtes indépendantes en parallèle, tout en conservant le registre partagé des quotas comme autorité avant chaque appel fournisseur.

## API Python
`CloudflareImageAdapter.generate_many(jobs, now=None)`

Chaque entrée doit contenir :
- `prompt` : instruction de génération ;
- `model` : identifiant de modèle Cloudflare autorisé ;
- `idempotency_key` : clé unique par image.

Le résultat conserve l'ordre d'entrée. Chaque image retourne `status=generated` ou `status=failed` avec une erreur exploitable. Une erreur sur une image ne supprime pas les images déjà générées avec succès.

## Contrôle de concurrence
- Valeur par défaut : 4 requêtes simultanées.
- Réglage par instance : `max_concurrency`, de 1 à 16.
- Taille maximale d'un lot : 500 entrées.
- Les clés d'idempotence dupliquées dans un même lot sont rejetées avant tout appel réseau.
- Chaque requête passe individuellement par la réservation transactionnelle ; les appels qui dépassent le quota sont bloqués avant le fournisseur.
- La concurrence augmente le débit uniquement si le compte fournisseur, le modèle et les quotas autorisent ces requêtes. Elle ne crée pas de quota supplémentaire et ne garantit pas un débit contractuel.

## Recommandation de démarrage
Démarrer à 4 workers, mesurer le temps moyen, le taux d'échec et les unités consommées, puis augmenter progressivement jusqu'à 8 ou 16 uniquement si les réponses fournisseur et les limites de compte le permettent. Ne jamais contourner les réservations pour gagner de la vitesse.

## Limites
- L'adaptateur retourne les octets d'image ; le stockage, la validation visuelle, la génération de PDF et la publication KDP restent des étapes séparées.
- Aucun appel réel Cloudflare n'a été effectué pendant cette mission.
- Les coûts par modèle doivent être confirmés par des mesures/documentation de compte ; les estimations erronées peuvent réduire le nombre d'images traitées.
- Les erreurs ambiguës conservent les réservations et nécessitent rapprochement ; aucune relance automatique n'est effectuée.

## Sécurité
Aucun secret n'est inclus dans les lots ou les résultats. La clé service_role reste côté serveur. Les lots ne déclenchent aucun fournisseur payant de secours.
