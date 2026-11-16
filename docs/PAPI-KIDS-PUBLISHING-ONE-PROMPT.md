# PAPI KIDS PUBLISHING — ONE PROMPT → COMPLETE BOOK

## 1. Décision produit

La fonction prioritaire de PAPI KIDS PUBLISHING est la génération d'un livre jeunesse complet à partir d'une seule requête utilisateur. L'utilisateur décrit le résultat souhaité une fois ; le système transforme ce brief en dossier de production, coordonne les spécialistes, fabrique les livrables, contrôle leur qualité et présente un dossier final à valider.

**Promesse produit visée :** une requête → un livre complet prêt pour validation humaine et préparation KDP. Cette promesse n'est pas déclarée opérationnelle tant que le test de bout en bout défini ci-dessous n'a pas réussi.

## 2. Expérience utilisateur

Entrée minimale : texte libre, par exemple « Crée un livre illustré pour enfants de 6 à 9 ans sur une petite fille qui découvre une planète magique ».

Le système doit :
- extraire les paramètres explicitement donnés ;
- choisir des valeurs par défaut raisonnables pour les paramètres absents ;
- ne poser une question que si une information est indispensable ou si une décision présente un risque important ;
- afficher un brief interprété modifiable avant la production lorsque le coût de génération est significatif ;
- conserver un identifiant de projet et permettre reprise, révision et régénération ciblée.

Paramètres du brief : langue, tranche d'âge, thème, genre, longueur, format (album illustré, roman illustré, manga, livre d'activités, etc.), ton, objectif pédagogique éventuel, contraintes de contenu, style visuel original, format de sortie et marché cible. Les valeurs non fournies sont proposées par défaut et signalées comme telles.

## 3. Orchestration spécialisée

Le directeur de production crée un dossier et un plan de travail avec dépendances. Les rôles suivants sont des responsabilités logiques ; ils ne deviennent des agents autonomes qu'après intégration et tests.

1. **PAPI DIRECTOR** — reçoit le brief, crée le projet, planifie, attribue, suit les dépendances et gère les reprises.
2. **MARKET RESEARCH** — étudie les tendances, les besoins des lecteurs et les catégories ; fournit des observations sourcées, sans copier une œuvre existante.
3. **STORY ARCHITECT** — définit la promesse narrative, le synopsis, la structure et le rythme.
4. **CHILDREN WRITER** — rédige le manuscrit original adapté à l'âge.
5. **EDUCATIONAL EXPERT** — vérifie vocabulaire, lisibilité, cohérence pédagogique et adéquation à l'âge.
6. **CHARACTER DESIGNER** — établit la bible des personnages, attributs visuels et règles de continuité.
7. **ART DIRECTOR** — définit la direction artistique, palette, composition et références originales.
8. **ILLUSTRATION TEAM** — produit les illustrations requises, page par page ou scène par scène, selon un brief visuel validé.
9. **BOOK DESIGNER** — compose les pages, typographie, marges, pagination et éléments liminaires.
10. **COVER DESIGNER** — prépare couverture avant, dos et quatrième de couverture selon le format d'impression retenu.
11. **KDP SPECIALIST** — vérifie les paramètres techniques et prépare les métadonnées et fichiers adaptés aux exigences Amazon KDP en vigueur.
12. **QUALITY CONTROL / MARIAMA** — effectue une revue indépendante éditoriale, visuelle, linguistique et technique.
13. **IP & COPYRIGHT** — contrôle les risques de plagiat, marques, personnages protégés, images sous licence et droits des contributions.

Chaque tâche possède un responsable, des entrées, des sorties attendues, un statut, des critères d'acceptation, des preuves et un historique de versions. Les agents ne peuvent pas approuver leur propre travail critique : le contrôle final est indépendant.

## 4. Chaîne de production

États recommandés du projet :

`RECEIVED → BRIEF_READY → RESEARCHED → OUTLINED → MANUSCRIPT_DRAFT → MANUSCRIPT_APPROVED → CHARACTER_BIBLE_READY → ART_DIRECTION_READY → ILLUSTRATIONS_READY → INTERIOR_COMPOSED → COVER_READY → PREFLIGHT_PASSED → HUMAN_APPROVAL → RELEASE_PACKAGE_READY`

Les états d'échec et d'attente doivent être explicites : `NEEDS_INPUT`, `BLOCKED`, `RETRYING`, `FAILED`, `CANCELLED`. Chaque transition vérifie ses prérequis ; aucune étape ne peut être marquée terminée sans livrable et preuve.

Ordre d'exécution :
1. Analyser la demande et produire le brief structuré.
2. Étudier le marché et proposer un angle différenciant.
3. Écrire le synopsis, le plan et le manuscrit complet.
4. Faire relire et corriger le manuscrit.
5. Verrouiller la bible des personnages et la direction artistique.
6. Générer les illustrations avec des identifiants de scènes/pages et des contrôles de cohérence.
7. Composer l'intérieur et calculer le nombre de pages réel.
8. Déterminer le format KDP, le papier, le fond perdu et le gabarit de couverture selon les spécifications à jour.
9. Générer la couverture à partir du gabarit exact, avec dos calculé selon le nombre de pages et le papier.
10. Produire les fichiers numériques appropriés et les métadonnées de vente.
11. Effectuer les contrôles automatisés et une revue indépendante.
12. Constituer le dossier de livraison et demander l'approbation humaine avant toute publication.

## 5. Livrables attendus

Selon le type de livre :
- brief structuré et fiche de projet ;
- titre, sous-titre, synopsis et manuscrit intégral ;
- découpage en pages ou chapitres ;
- bible des personnages et guide de continuité ;
- illustrations originales en haute résolution, reliées aux pages/scènes ;
- fichier intérieur PDF conforme au format d'impression choisi ;
- couverture complète calculée sur les dimensions et le nombre de pages réels ;
- EPUB ou autre fichier numérique lorsque le format s'y prête ;
- description commerciale, mots-clés et suggestions de catégories ;
- rapport de contrôle qualité, rapport de conformité et liste des points restant à valider ;
- manifeste des fichiers avec versions, dimensions, empreintes et statut de validation.

Ne pas promettre systématiquement un EPUB pour les formats dont la mise en page fixe est essentielle ; choisir le format numérique adapté ou expliquer la limite.

## 6. Qualité, droits et sécurité

- Œuvres, textes et illustrations doivent être originaux ; l'analyse de marché ne doit jamais conduire à reproduire le style distinctif, les personnages, le texte ou la composition reconnaissable d'un tiers.
- Enregistrer la provenance et les conditions d'utilisation des ressources externes.
- Contrôler orthographe, grammaire, répétitions, cohérence narrative, continuité des personnages, lisibilité, marges, polices incorporées, résolution, fond perdu, dimensions et pagination.
- Contrôler que les images ne contiennent pas de texte parasite, de signatures, de filigranes ou d'éléments incohérents.
- Refaire uniquement les tâches en échec lorsque leurs dépendances restent valides ; invalider les livrables aval si une modification amont les rend obsolètes.
- Journaliser les versions, erreurs, reprises et coûts estimés/réels.
- Aucun achat, abonnement, appel payant, dépense publicitaire, publication ou engagement commercial sans autorisation explicite du propriétaire.
- La publication KDP reste une action humaine approuvée. Le système prépare les fichiers ; il ne prétend pas publier sans accès, autorisation et test réel.

## 7. Architecture technique cible

Composants à implémenter :
- `BookRequest` : requête brute et paramètres extraits.
- `BookProject` : identité, statut, marché, langue, format, paramètres et version.
- `ProductionTask` : rôle responsable, dépendances, tentatives, statut et critères d'acceptation.
- `BookAsset` : type, chemin/URI, version, dimensions, format, empreinte, provenance et statut de validation.
- `ReviewReport` : contrôles, anomalies, sévérité, preuves, correctifs et décision.
- `ReleasePackage` : manifeste des livrables, métadonnées et approbation humaine.
- `ProviderAdapter` : interface remplaçable pour modèles de texte, génération d'images et composition de documents ; aucun fournisseur ni quota n'est supposé gratuit ou disponible avant vérification.
- `JobOrchestrator` : exécution idempotente, reprise, limites de tentatives, délais, déduplication et arrêt d'urgence.

Les secrets restent dans les variables sécurisées ou un coffre, jamais dans le dépôt. Les fichiers lourds doivent être conservés dans un stockage d'objets autorisé ; le dépôt Git conserve le code, les schémas et la documentation, pas les images finales volumineuses.

## 8. Critères d'acceptation du pilote

Le pilote n'est réussi que si une seule requête utilisateur produit, sans demandes successives pour chaque livrable :
1. un manuscrit complet cohérent et adapté à l'âge annoncé ;
2. une bible de personnages et une direction artistique ;
3. toutes les illustrations nécessaires, correctement associées aux pages ;
4. un PDF intérieur qui passe les contrôles techniques du format choisi ;
5. une couverture complète aux dimensions exactes calculées ;
6. les métadonnées commerciales et un rapport de contrôle ;
7. un dossier final téléchargeable avec manifeste et versions ;
8. un parcours de reprise démontré après au moins un échec simulé ;
9. une validation humaine obligatoire avant publication.

Le test doit être reproductible, consigner les versions des modèles/outils et distinguer les contrôles automatisés des vérifications humaines. Un prototype documentaire ou une génération partielle ne satisfait pas ces critères.

## 9. Indicateurs

Indicateur principal : nombre de livres complets acceptés après une seule requête.

Indicateurs secondaires : taux de réussite de bout en bout, taux de reprises, temps de production, coût par livre, taux d'illustrations acceptées au premier essai, anomalies par livre, conformité technique au premier contrôle et taux de validation humaine.

## 10. Découpage d'implémentation

- **Lot 1 — Spécification et contrats de données :** schémas, statuts, dépendances, manifeste et critères d'acceptation.
- **Lot 2 — Orchestrateur :** création de projet depuis un seul prompt, planification, idempotence, reprises et journalisation.
- **Lot 3 — Adaptateurs IA :** fournisseur de texte et fournisseur d'images configurables, limites, coûts et gestion d'erreurs.
- **Lot 4 — Production éditoriale :** manuscrit, bible personnages, illustrations et contrôles de cohérence.
- **Lot 5 — Composition :** PDF intérieur, couverture et format numérique adapté.
- **Lot 6 — Préflight et livraison :** validation, rapport, métadonnées, paquet final et approbation humaine.
- **Lot 7 — Test réel :** produire un livre complet pilote, mesurer les coûts et corriger les défauts avant toute déclaration de mise en service.

**Statut initial de ce document :** spécification créée. Aucun moteur ONE PROMPT, agent de publication ou pipeline KDP n'est déclaré implémenté ou opérationnel par la création de ce document seule.
