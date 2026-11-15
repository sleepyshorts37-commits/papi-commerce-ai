# Mission 117 — Journal immuable des contrôles qualité d'images

## Objectif
Conserver une trace vérifiable de chaque contrôle qualité automatisé, reliée à l'empreinte SHA-256 exacte de l'image, sans confondre résultat automatique et validation humaine.

## Livrables
- `runtime/papi_core/image_quality_audit.py` : journal d'événements JSON immuables, création atomique sans écrasement.
- Identifiant d'événement unique avec rejeu idempotent uniquement si le contenu est identique.
- Refus de réutiliser un identifiant pour un événement différent.
- Validation de l'identité du livre, de la page, du statut et de l'empreinte de l'image.
- Verrouillage du statut automatisé : aucune valeur `approved` et aucun champ d'approbation humaine ne peuvent être acceptés.
- Tests de rejeu, collision, intégrité, statut et séparation des événements.

## Utilisation
Le journal reçoit le rapport produit par `review_generated_image` et le conserve dans un volume privé persistant :

`ImageQualityAuditLog(root="/data/papi-quality-audit").append(...)`

La lecture filtrée s'effectue avec `list_events(book_id=..., page_id=...)`.

## Sécurité et limites
- Aucun appel réseau, fournisseur de vision, Cloudflare ou Supabase.
- Aucun secret, aucun service payant, aucun worker permanent.
- Le journal est append-only au niveau applicatif : les événements existants ne sont jamais remplacés. La protection contre la suppression par un administrateur du système de fichiers dépend des permissions et sauvegardes du volume.
- Le journal ne constitue pas une preuve d'identité du réviseur ni un mécanisme d'authentification.
- La validation humaine reste un processus séparé et obligatoire avant assemblage ou publication.

## Validation
Les tests sont fournis dans `tests/test_image_quality_audit.py`. Le résultat CI GitHub sera consulté avant de déclarer la mission terminée.
