# PAPI AGENT FACTORY — Architecture d'expansion continue (1.66)

## Objectif
Construire une entreprise multi-départements capable d'ajouter continuellement les métiers, compétences et agents nécessaires à sa croissance. L'objectif initial est d'environ 50 agents ; ce nombre n'est pas un plafond. La croissance peut être sans limite numérique prédéfinie, mais elle reste justifiée par la demande, la valeur créée, les coûts, les risques et la capacité réelle d'exploitation.

## Gouvernance
- **Ibrahima — Architecte et responsable de PAPI AGENT FACTORY** : propriétaire du processus de conception et d'évolution de l'organisation.
- **Malik — Scout des métiers et compétences** : adjoint d'Ibrahima, spécialisé dans la découverte des professions existantes et émergentes, tous secteurs confondus.
- **Awa — Scout stratégique** : rattachée à PAPI OPPORTUNITY ; transforme les signaux de marché en opportunités commerciales qualifiées.
- **Mariama** : contrôle qualité indépendant des fiches, tests et résultats.
- **Cheikh Fall** : surveillance de la fiabilité technique, des erreurs, des quotas et des dépendances.
- **Astou** : coordination et arbitrage inter-départements.
- **Marietou Diouf** : coordination opérationnelle et suivi des responsables.

## Processus permanent

### 1. Observer
Malik analyse les sources publiques et professionnelles disponibles :
- offres d'emploi et compétences recherchées ;
- besoins récurrents des entreprises et consommateurs ;
- nouveaux métiers et spécialisations ;
- évolutions réglementaires et technologiques ;
- nouvelles catégories de services commercialisables ;
- pratiques concurrentielles documentées.

Chaque signal doit être daté, sourcé et accompagné d'un niveau de confiance. Les tendances non vérifiées restent des hypothèses.

### 2. Qualifier le besoin
Pour chaque métier ou capacité repéré, Malik remet une fiche :
- intitulé du métier et variantes ;
- secteurs concernés ;
- problèmes clients résolus ;
- demande observée et sources ;
- compétences et outils nécessaires ;
- possibilités de vente et clientèle cible ;
- revenus potentiels estimés, hypothèses explicites ;
- coûts, dépendances et contraintes d'accès ;
- risques juridiques, de confidentialité et de réputation ;
- recommandation : tester, différer ou rejeter.

### 3. Détecter les lacunes internes
Ibrahima compare les besoins retenus à l'organigramme et aux fiches existantes. Il recherche les doublons, les tâches non couvertes, les goulots d'étranglement et les compétences insuffisantes. Il privilégie la formation ou l'extension d'un rôle existant lorsqu'elles sont plus efficaces que la création d'un nouvel agent.

### 4. Concevoir un agent
Chaque proposition de nouvel agent comporte :
- identifiant immuable et unique ;
- nom complet distinct ;
- département et équipe ;
- fonction et responsable hiérarchique ;
- mission, périmètre et livrables ;
- compétences et limites de compétence ;
- objectifs et KPI mesurables ;
- outils requis et alternatives gratuites ;
- niveau d'autonomie ;
- permissions positives et actions interdites ;
- données accessibles et règles de conservation ;
- date de création, statut et historique des affectations/évaluations.

### 5. Évaluer la valeur
Avant intégration, Ibrahima estime :
- valeur client et potentiel de chiffre d'affaires ;
- économies de temps ou de coûts ;
- coût total de possession, y compris API, hébergement et maintenance ;
- délai de mise en service ;
- risques et dépendances ;
- chevauchement avec les rôles existants.

Avec le budget autorisé de 0 XOF, toute proposition nécessitant une dépense, un abonnement ou un crédit payant est mise en attente jusqu'à autorisation explicite. Les estimations ne sont jamais comptabilisées comme des revenus.

### 6. Construire et tester
- rédiger les instructions et scénarios ;
- définir des entrées/sorties structurées ;
- tester les cas normaux, limites, erreurs et tentatives d'abus ;
- vérifier les permissions et l'isolation des données ;
- faire évaluer les résultats par Mariama ;
- documenter les limites et la procédure d'arrêt.

Un profil documentaire, un prototype testé et un agent déployé sont trois états différents et doivent être affichés séparément.

### 7. Intégrer et mesurer
Après les validations requises, le profil peut être proposé à l'intégration. Les KPI sont suivis sur des résultats observables : qualité, délai, taux d'erreur, satisfaction, coût, opportunités qualifiées, ventes encaissées et économies réalisées. Les objectifs sont adaptés au métier ; aucun agent ne doit être évalué sur des métriques artificielles.

### 8. Améliorer ou retirer
Ibrahima peut proposer de former, spécialiser, fusionner, remplacer ou retirer un profil. Mariama vérifie les preuves. Les changements de permissions sensibles, les coûts et les engagements externes restent soumis aux autorisations humaines prévues.

## Règle obligatoire d'unicité des noms
Aucun nom d'agent ne peut être attribué à deux personnes/agents dans PAPI COMMERCE AI, quel que soit le département, le niveau hiérarchique, la nationalité ou la langue d'origine.
- Chaque agent doit avoir un **nom d'affichage complet unique** et un **prénom d'usage unique** dans le registre global. Si un prénom est déjà attribué, choisir un autre prénom, même si les agents ont des fonctions ou départements différents.
- La règle s'applique sans exception aux prénoms sénégalais, africains et internationaux, ainsi qu'aux noms composés, surnoms et pseudonymes utilisés professionnellement.
- Vérifier les collisions en ignorant la casse, les accents, les espaces, les traits d'union et les variantes typographiques ; vérifier aussi les alias et translittérations connus afin d'éviter les doublons évidents.
- Si une collision est détectée, le nouvel agent reçoit un autre nom distinct avant que sa fiche soit validée. Si deux fiches historiques sont déjà en conflit, proposer un renommage explicite et conserver l'ancien nom uniquement dans l'historique d'audit, jamais comme nom d'usage actif.
- L'identifiant technique unique ne remplace jamais l'obligation d'avoir un nom humain distinct.
- Tenir un registre central des noms attribués et effectuer un contrôle automatique de collision à chaque création, renommage ou réactivation d'agent. En cas de doute, bloquer la validation et demander un arbitrage humain.

## Cycle de travail
1. Malik découvre un métier ou une compétence.
2. Il documente la demande et les preuves.
3. Ibrahima évalue le besoin organisationnel.
4. Ibrahima conçoit le profil et son rattachement.
5. Le registre central vérifie l'unicité du nom et de l'identité.
6. Mariama contrôle la qualité et les risques.
7. Cheikh Fall vérifie les dépendances et la fiabilité.
8. Marietou/Astou coordonnent l'intégration selon la gouvernance.
9. Les performances sont mesurées et le profil est amélioré.

## Cadence proposée
- Quotidien : collecte de signaux et veille légère.
- Hebdomadaire : revue des métiers, lacunes et propositions prioritaires.
- Mensuel : revue de portefeuille des agents, coûts, résultats, doublons et restructurations.
- Déclenchement immédiat : nouvelle demande client, incident majeur, changement réglementaire ou compétence critique manquante.

Cette cadence décrit une cible de fonctionnement ; elle n'est pas active tant que le scheduler et les sources ne sont pas déployés et testés.

## Garde-fous non négociables
- Budget initial : 0 XOF ; aucun achat, abonnement ou crédit payant sans autorisation.
- Aucun secret, mot de passe, token, OTP, PIN ou donnée bancaire dans le dépôt.
- Aucun agent ne contacte un tiers, publie, contracte, achète, retire ou transfère de l'argent sans autorisation explicite et permission dédiée.
- Respect des lois, des conditions des plateformes, des droits d'auteur, de la vie privée et des règles anti-spam.
- Les agents ne créent pas d'autres agents runtime en production par simple auto-autorisation. Ibrahima peut concevoir et tester des profils dans un environnement contrôlé ; l'activation suit le processus de validation et de déploiement.
- La création sans plafond numérique ne signifie pas ressources infinies : la capacité réelle reste limitée par le budget, le calcul, les quotas, la sécurité et la supervision.
- Toute identité doit être unique et non usurpable ; les collisions de noms sont résolues avant activation.

## État au moment de cette proposition
Ce document définit le processus cible. Il ne prouve pas que Malik, Awa ou la fabrique d'agents sont déployés, qu'une veille automatique tourne, ni que des agents runtime peuvent se créer eux-mêmes. Les profils restent planifiés tant que les implémentations, tests, accès et déploiements nécessaires ne sont pas achevés.

## Décisions de nommage à traiter
- **Awa** existe déjà dans la liste historique PAPI MARKET comme analyste d'étude de marché. Le rôle de Scout PAPI OPPORTUNITY doit recevoir un autre prénom et un nom complet distincts avant activation.
- **Malik** est proche de **Malick**, déjà affecté aux missions freelance. Pour respecter la règle stricte d'unicité, le nouvel agent Scout des métiers doit recevoir un autre prénom d'usage et un nom complet distincts avant activation.
