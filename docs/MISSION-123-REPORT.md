# Mission 123 — Pipeline de contrôle qualité et audit des assets

## Implémentation
Le nouveau service \`review_pkp0001_assets\` parcourt les images PKP-0001 en attente de revue, vérifie l'intégrité des octets, appelle le réviseur vision uniquement s'il est explicitement fourni, puis écrit un événement d'audit append-only lié à l'empreinte SHA-256 de l'image.

## Statuts
- Image techniquement valide sans réviseur : \`awaiting_visual_review\`.
- Tous les contrôles sémantiques passent : \`pending_human_approval\`.
- Échec d'un contrôle : \`blocked\`.
- Aucun statut automatisé ne vaut approbation humaine ou autorisation de publication.

## Sécurité
- Maximum 24 images examinées par exécution.
- Prompt de chaque page requis.
- Audit déterministe/idempotent pour le même contenu.
- Aucun appel externe par défaut ; le réviseur vision est injecté par l'application.
- Pas de déploiement ni d'appel API image.
