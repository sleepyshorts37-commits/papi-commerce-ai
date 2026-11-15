# Mission 166 — Validation des métadonnées de fiche Amazon KDP

## Livrable
- Vérifie titre, auteur, description, langue, jusqu'à 7 mots-clés, jusqu'à 3 catégories, tranche d'âge, droits commerciaux, titulaire/preuve, territoires, marketplace, devise et prix daté.
- Contrôle le choix d'ISBN broché : ISBN gratuit KDP ou ISBN-13 personnel avec éditeur déclaré.
- Valide le checksum ISBN-13.
- Mode ebook distinct : refuse de reprendre par erreur l'ISBN imprimé.
- Retourne les champs normalisés et les blocages ; n'invente aucune donnée absente.
- Même dossier complet, le statut reste \`ready_for_owner_review\`, jamais prêt à téléverser.
