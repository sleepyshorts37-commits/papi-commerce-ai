# PAPI IMAGE FACTORY — Planificateur de production et manifeste des images

## Objectif
Transformer un livre ou une série d'illustrations en lots de génération prêts à exécuter, afin de réduire les opérations manuelles et d'exploiter le parallélisme disponible sans dépasser les limites fournisseur.

## Module
`runtime/papi_core/image_factory.py`

### Planification
`plan_book_images(...)` :
- vérifie les identifiants, les pages, les prompts et les doublons ;
- refuse un modèle absent du registre des coûts autorisés ;
- ordonne les pages par priorité (`urgent`, `high`, `normal`, `low`), puis par numéro ;
- produit des clés d'idempotence déterministes compatibles avec le registre partagé ;
- découpe les travaux selon une taille maximale et un budget d'unités estimées par lot ;
- ne réalise aucun appel réseau.

### Exécution
`execute_image_batch(adapter, batch)` :
- soumet explicitement un lot à `generate_many` ;
- exige un résultat par image ;
- ne relance pas automatiquement les échecs.

Les erreurs ambiguës et les réservations incertaines restent soumises à la procédure de rapprochement du quota ; elles ne doivent jamais être relancées à l'aveugle.

### Manifeste d'assets
`build_asset_manifest(...)` produit un manifeste JSON de métadonnées :
- livre, page, numéro, modèle et clé d'idempotence ;
- empreinte SHA-256 et taille des octets pour les images générées ;
- type MIME, statut `pending_visual_review` ou `generation_failed` ;
- `human_approved=false` par défaut.

Les octets de l'image ne sont pas copiés dans le manifeste. Le stockage durable (Supabase Storage ou stockage objet) est une étape ultérieure, avec une politique de rétention et des permissions explicites.

## Exemple de découpage
Pour 24 pages, un coût estimé de 100 unités par image, une limite de 8 images et 800 unités par lot :
- 3 lots de 8 images ;
- maximum estimé de 800 unités par lot ;
- clés stables pour reprendre un plan identique sans créer de nouvelles intentions.

La valeur 100 est illustrative, pas une mesure Cloudflare ni un quota garanti.

## Contrôle qualité
Une image générée n'est pas une image approuvée. Le manifeste la place en attente de revue visuelle. Les contrôles de personnages, style, sécurité, lisibilité, composition, droits et adéquation au brief restent requis avant assemblage ou publication.

## Sécurité et limites
- Mode gratuit strict : aucun fournisseur payant ou inconnu.
- Le routeur doit transmettre un modèle dont le coût est explicitement enregistré.
- Aucun worker n'est activé automatiquement.
- Aucun stockage cloud ou appel fournisseur n'est déclenché par la planification.
- Aucun quota quotidien global n'est présumé par le planificateur ; le registre partagé reste l'autorité au moment de chaque génération.
