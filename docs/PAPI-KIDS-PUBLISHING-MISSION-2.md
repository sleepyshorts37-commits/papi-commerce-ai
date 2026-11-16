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


## Mission 3 — Cycle de vie des tâches (socle local)

Ajouté après le premier plan ONE PROMPT :
- transitions explicites `start`, `complete`, `fail`, `retry` ;
- blocage du démarrage tant que les dépendances ne sont pas terminées ;
- persistance atomique des mises à jour JSON ;
- historique horodaté des événements et références de livrables ;
- trois tentatives maximum par tâche ;
- commandes CLI `book-task` pour piloter une tâche ;
- exécution réelle des agents toujours désactivée.

Limites : aucun agent IA, générateur de texte ou d'images, stockage cloud, interface mobile ou publication KDP n'est encore connecté. Les tests unitaires ajoutés pour ces transitions doivent être exécutés dans un environnement Python avant de déclarer cette étape validée.


## Mission 4 — Registre des livrables, revues et manifeste

Le moteur gère maintenant :
- un registre de livrables avec identifiant, type, URI, version, empreinte SHA-256, provenance et statut ;
- des rapports de revue avec réviseur distinct de l'acteur qui soumet le rapport ;
- la préparation d'un manifeste de livraison listant les livrables et leurs empreintes ;
- le blocage du manifeste si une tâche n'est pas terminée, si un livrable n'est pas approuvé ou si une revue n'est pas approuvée ;
- un statut de validation propriétaire pending_owner et une publication explicitement marquée not_published.

Limites : le registre stocke les métadonnées et références, pas les fichiers eux-mêmes. Aucun fichier PDF, EPUB ou visuel n'est généré ou téléversé. La validation humaine et la publication KDP ne sont pas exécutées.


## Mission 5 — Contrat des fournisseurs IA et garde-fous

Ajout du module `runtime/papi_core/providers.py` :
- contrat commun de requête/résultat pour les tâches de texte et d'image ;
- registre explicite des fournisseurs et vérification de leurs capacités ;
- fournisseur `mock` local déterministe pour tester le parcours sans réseau ;
- politique fermée par défaut : fournisseur autorisé, plafond XOF, accord propriétaire et secret d'environnement requis pour tout fournisseur externe ;
- résultats simulés clairement marqués ; empreinte SHA-256 du contenu retourné.

**Limites importantes :** aucun fournisseur réel (OpenAI, Google ou autre) n'est connecté. Le mock ne rédige pas de livre et ne dessine pas d'illustration. Aucun appel réseau, secret, abonnement ou paiement n'est utilisé. La prochaine étape sera l'intégration d'un fournisseur réel uniquement après choix du prestataire, vérification des tarifs et accord explicite.


## Mission 6 — Structure, validation et assemblage du manuscrit

Ajout de `runtime/papi_core/manuscript.py` :
- schéma de manuscrit structuré : titre, langue, âge cible, synopsis, chapitres et briefs d'illustration ;
- validation des champs, bornes, tranches d'âge et marqueurs provisoires ;
- comptage de mots, empreinte SHA-256 et avertissements éditoriaux ;
- assemblage du contenu validé en Markdown.

**Limites :** ce module contrôle la structure, pas la qualité littéraire, la sécurité psychologique ou la justesse pédagogique. Il ne génère pas le texte, ne produit pas de PDF/EPUB et ne remplace pas une relecture humaine.


## Mission 7 — Première sortie numérique EPUB 3

Ajout de `runtime/papi_core/epub.py` :
- assemblage d'un fichier EPUB 3 depuis un manuscrit validé ;
- génération du conteneur, du manifeste OPF, du sommaire de navigation, des pages XHTML et du CSS ;
- échappement des contenus textuels et contrôle d'intégrité de l'archive ZIP ;
- inspection minimale du paquet et calcul SHA-256.

**Limites :** ce premier EPUB n'intègre pas encore de couverture ni d'images. L'inspection interne n'est pas une validation EPUBCheck officielle ni une garantie d'acceptation KDP. Le fichier doit être vérifié avec les outils de préflight appropriés et relu avant commercialisation.


## Mission 8 — Épreuve PDF intérieure

Ajout de `runtime/papi_core/print_pdf.py` et de ReportLab :
- création d'une épreuve PDF texte à partir du manuscrit validé ;
- formats de coupe configurables dans des limites définies ;
- marges et gouttière configurables, pagination et métadonnées PDF ;
- vérification minimale de l'en-tête et de la fin du fichier PDF.

**Limites :** il s'agit d'une épreuve intérieure textuelle, sans illustrations ni couverture. Les marges par défaut ne sont pas une certification KDP : les exigences exactes dépendent du format, du papier, du fond perdu et du nombre final de pages. Un préflight KDP reste obligatoire.
