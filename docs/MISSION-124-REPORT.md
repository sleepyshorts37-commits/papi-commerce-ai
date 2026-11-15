# Mission 124 — Contrat de préflight KDP

## But
Empêcher la fabrication finale d'utiliser des dimensions, marges, fonds perdus, gouttières ou résolutions devinés.

## Implémentation
Le module \`kdp_print_preflight.py\` compare un manifeste d'inspection PDF/image à un gabarit KDP officiel, daté de moins de 30 jours. Il vérifie format de coupe, pagination, polices incorporées, ordre des pages, contrôle des pages blanches, marges, gouttière, 24 images, DPI effectif et empreintes SHA-256.

## Limite
Le module valide les résultats fournis par un inspecteur PDF externe/interne ; il ne lit pas encore les octets PDF et ne calcule pas lui-même le gabarit de couverture. Il ne délivre qu'un statut \`ready_for_human_review\`, jamais une autorisation de téléversement.

## Tests
Tests hors réseau pour manifeste conforme, images manquantes, DPI insuffisant, dimensions erronées, polices non incorporées, gabarit ancien/non officiel et données manquantes.
