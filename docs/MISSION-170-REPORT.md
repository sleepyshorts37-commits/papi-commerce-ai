# Mission 170 — Orchestrateur du package broché KDP

## Livrable
- Assemble le générateur PDF intérieur et le générateur de couverture full-wrap dans un package unique.
- Exige pagination paire >=24, exactement une illustration approuvée par page, deux assets de couverture approuvés et le gabarit KDP officiel stocké en privé avec SHA-256/source/date.
- Génère intérieur et couverture dans un répertoire staging privé, vérifie les PDF, les pages et les empreintes, puis publie le répertoire par renommage atomique.
- Rollback complet si un des deux PDF échoue ; aucune sortie partielle visible.
- Manifeste prêt pour le release gate avec les dimensions d'impression et les empreintes.
- Les deux PDF restent \`pending_manual_pdf_inspection\`; aucune soumission KDP ou publication.

## Limites
Les assets finaux, le gabarit téléchargé, les positions de texte et les choix d'impression doivent être validés avant le build. Le package builder ne déclenche aucun fournisseur image.
