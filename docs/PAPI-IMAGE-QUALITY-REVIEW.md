# Mission 116 — Contrôle qualité automatisé des illustrations

## Livrable
`runtime/papi_core/image_quality_review.py` ajoute une porte de contrôle qualité fail-closed avant assemblage du livre.

## Contrôles techniques locaux
- Signature PNG, JPEG ou WebP reconnue.
- Cohérence entre signature et type MIME déclaré.
- Limite de taille configurable.
- Empreinte SHA-256 pour relier le rapport à l'asset exact.

## Revue sémantique par adaptateur de vision
Le module définit un contrat injectable pour un réviseur visuel. Il exige six dimensions structurées :
1. conformité au prompt ;
2. cohérence des personnages ;
3. cohérence du style ;
4. composition ;
5. lisibilité ;
6. sécurité du contenu.

Chaque dimension doit fournir un score de 0 à 1, un booléen `passed` et une liste de constats. Un contrôle manquant, échoué ou sous le seuil bloque l'image.

## Limite importante
Cette mission n'intègre pas encore un modèle de vision réel : aucun fournisseur ou service de vision n'a été sélectionné, configuré ou appelé. Sans adaptateur, l'image reste `awaiting_visual_review`. Le contrat permet de connecter ultérieurement un fournisseur gratuit validé, sans inventer une capacité de vision qui n'existe pas encore.

## Gouvernance
Même si les six contrôles passent, le statut reste `pending_human_approval`. Le module ne peut jamais définir `human_approved=true`, publier, assembler automatiquement ou relancer un appel fournisseur. Les décisions finales et la validation visuelle restent humaines.

## Tests
Tests avec réviseur simulé, sans réseau ni dépense : signature invalide, MIME incohérent, limite de taille, réviseur absent, échec sécurité, réponse mal formée et validation en attente d'approbation humaine.
