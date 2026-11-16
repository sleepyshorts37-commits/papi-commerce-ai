# Mission 2 — Premier moteur ONE PROMPT

## Livré dans ce lot
- Création d'un projet PAPI KIDS à partir d'une seule demande textuelle.
- Interprétation prudente de la langue, de la tranche d'âge et du type de livre ; les valeurs par défaut sont signalées.
- Plan de production de 13 tâches avec rôles et dépendances.
- Identifiant déterministe fondé sur SHA-256 : répéter la même demande dans le même stockage retrouve le même projet.
- Stockage JSON local avec permissions restrictives et création exclusive.
- Validation du schéma, des dépendances et des garde-fous.

## Commandes
\`\`\`bash
PYTHONPATH=runtime python -m papi_core book-create "Crée un album illustré pour enfants de 6 à 9 ans sur une tortue courageuse"
PYTHONPATH=runtime python -m papi_core book-show PKP-<16-caractères-hex>
PYTHONPATH=runtime python -m unittest discover -s tests -v
\`\`\`

Par défaut, les projets sont enregistrés dans \`data/book_projects/\`. Ce dossier peut être remplacé avec \`--store-dir\`.

## Limites explicites
Ce lot crée le dossier et le plan, pas le livre. Aucun fournisseur IA, générateur d'images, moteur PDF/EPUB, stockage cloud, agent autonome ou intégration KDP n'est connecté. Les 13 tâches restent en \`backlog\`, \`execution_enabled=false\`. L'approbation humaine avant publication est obligatoire.

## Prochaine étape
Ajouter des transitions de tâches persistantes, les actifs et rapports de revue, puis connecter un premier fournisseur de génération uniquement après vérification des coûts et autorisation explicite.
