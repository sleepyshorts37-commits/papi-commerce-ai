# Mission 125 — Raccordement des sources éditoriales PKP-0001

## Sources intégrées
Copie contrôlée depuis les branches documentaires Mission 77 et Mission 89 :
- manuscrit V2 de 24 pages ;
- bible graphique V1 ;
- storyboard V1 ;
- brief de production des illustrations ;
- registre d'assets ;
- revues éditoriales V1 et V2 ;
- préflight d'assemblage imprimé ;
- manuscrit V1 conservé comme historique.

Le texte V2 reste une version de travail non approuvée. La bible graphique et le storyboard restent des spécifications non approuvées.

## Intégration technique
\`prepare_pkp0001_from_project_sources\` charge les sources versionnées du dépôt, vérifie les 24 pages du manuscrit, les 24 lignes du storyboard et les 24 prompts, puis calcule des empreintes SHA-256 et transmet les prompts/bible au registre et à l'orchestrateur.

## Gouvernance
- Aucun texte inventé ou réécrit dans ce raccordement.
- L'approbation éditoriale indépendante reste obligatoire.
- La préparation de campagne n'exécute aucune génération.
- Aucun agent externe, aucun appel API, aucune dépense, aucun déploiement ni publication.
