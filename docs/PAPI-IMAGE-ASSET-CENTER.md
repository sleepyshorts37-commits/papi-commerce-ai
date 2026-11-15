# PAPI IMAGE ASSET CENTER — bibliothèque et reprise de production

## Objectif
Conserver les images produites, retrouver rapidement les assets d'un livre, vérifier leur intégrité et reprendre le travail sans solliciter à nouveau le fournisseur pour une image déjà enregistrée.

## Implémentation
Module : `runtime/papi_core/image_asset_center.py`

- Stockage local durable via un volume privé persistant.
- Fichiers image séparés des métadonnées JSON.
- Écriture atomique et empreinte SHA-256.
- Formats acceptés : PNG, JPEG et WebP, vérifiés par signature binaire.
- Limite de taille configurable (25 Mo par défaut).
- Clé d'idempotence : même clé + même contenu = replay sans écriture ; même clé + contenu différent = rejet.
- Liste des assets par livre et statut.
- Vérification de l'empreinte à la lecture.
- Reprise : retrouver les assets déjà présents et ne planifier que les pages manquantes côté orchestrateur.

## Contrôle qualité
Le module vérifie l'intégrité technique (format, taille, MIME et empreinte), pas la qualité artistique. L'approbation visuelle reste humaine et exige une identité de réviseur et une justification. Les images sont en attente de revue par défaut.

Checklist de revue recommandée :
1. conformité au brief et à la page ;
2. cohérence des personnages et accessoires ;
3. continuité du style et de la palette ;
4. cadrage, anatomie et artefacts ;
5. lisibilité et absence de texte parasite ;
6. sécurité des enfants et adéquation à l'âge ;
7. droits et absence de contenu non autorisé.

## Sécurité et limites
- Aucun appel Cloudflare ou autre fournisseur.
- Aucun upload Supabase Storage ni changement de schéma.
- Aucun worker permanent.
- Le stockage local doit être un volume privé avec sauvegardes et permissions OS restrictives ; il n'est pas partagé entre plusieurs instances.
- Ne pas exposer les chemins locaux ou les métadonnées sensibles au navigateur.
- Le futur adaptateur objet devra appliquer les mêmes contrôles, clés d'idempotence et politiques d'accès.
- Une validation visuelle automatique peut assister le tri, mais ne doit pas approuver seule les images finales du livre.

## Utilisation
`LocalImageAssetCenter(root="/data/papi-assets").put(...)` enregistre une image déjà générée. `list_assets(book_id=...)` retrouve les éléments et `review(...)` inscrit une décision humaine. Ce module ne déclenche jamais la génération.
