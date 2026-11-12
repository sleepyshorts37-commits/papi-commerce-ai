# Registre central des 50 premiers agents — PAPI COMMERCE AI

## Objet et portée
Ce registre est la source de référence des postes du premier noyau de 50 agents. Il est extensible sans plafond numérique prédéfini : les identifiants sont stables et séquentiels, sans réutilisation après archivage.

**Important :** un poste inscrit n'est pas la preuve qu'un agent existe en runtime. Les 50 entrées ci-dessous sont des postes planifiés. Elles ne sont ni déployées ni opérationnelles par leur seule inscription.

## Règles d'identité
- L'identifiant technique `agent_id` est unique, immuable et indépendant du nom humain.
- Chaque agent activé doit avoir un prénom d'usage unique et un nom complet unique dans tout PAPI COMMERCE AI.
- La vérification est globale, tous départements et toutes nationalités confondus ; les noms internationaux sont soumis exactement à la même règle.
- Comparaison normalisée : casse, accents, espaces, traits d'union, ponctuation et variantes typographiques ignorés. Les alias, surnoms et translittérations évidentes sont également contrôlés.
- Toute collision bloque la validation. Un nouveau nom distinct doit être choisi avant activation.
- Les noms historiques ne sont pas automatiquement considérés comme validés. Ils sont conservés comme références de migration/audit, jamais comme noms d'usage tant que l'unicité n'est pas vérifiée.
- Aucun nom n'est inventé ou attribué silencieusement à une personne historique. Les champs de nom restent en attente jusqu'à validation de l'identité proposée.
- Les changements de nom sont journalisés ; un ancien nom reste dans l'historique privé d'audit et ne peut pas être réattribué.

## Répartition des 50 postes

| Département | Nombre |
|---|---:|
| Direction générale et gouvernance | 5 |
| PAPI OPPORTUNITY | 6 |
| PAPI SERVICES | 8 |
| PAPI MARKET | 7 |
| PAPI DROPSHIPPING | 5 |
| PAPI AFFILIATION | 4 |
| PAPI BUSINESS PARTNERS | 4 |
| PAPI COMMUNITY & MARKETING | 5 |
| PAPI FINANCE, RISQUES & ADMINISTRATION | 3 |
| PAPI TECH & AUTOMATISATION | 3 |
| **Total** | **50** |

## Registre des postes

| ID | Département | Poste / mission | Responsable fonctionnel |
|---|---|---|---|
| PAPI-001 | Direction | Président / propriétaire — arbitrages réservés | Gouvernance humaine |
| PAPI-002 | Direction | Direction générale — coordination opérationnelle | PAPI-001 |
| PAPI-003 | Direction | Intelligence centrale et synthèse stratégique | PAPI-001 |
| PAPI-004 | Direction | Architecture et expansion des agents (Agent Factory) | PAPI-002 |
| PAPI-005 | Direction | Audit indépendant et contrôle qualité | PAPI-001 |
| PAPI-006 | Opportunity | Scout des opportunités commerciales | PAPI-004 |
| PAPI-007 | Opportunity | Scout des métiers et compétences | PAPI-004 |
| PAPI-008 | Opportunity | Analyste de marché et demande client | PAPI-006 |
| PAPI-009 | Opportunity | Veille concurrentielle et benchmarking | PAPI-006 |
| PAPI-010 | Opportunity | Qualification des opportunités et scoring | PAPI-006 |
| PAPI-011 | Opportunity | Études de faisabilité et modèles économiques | PAPI-006 |
| PAPI-012 | Services | Responsable des prestations numériques | PAPI-002 |
| PAPI-013 | Services | Rédaction et édition professionnelle | PAPI-012 |
| PAPI-014 | Services | Traduction et localisation | PAPI-012 |
| PAPI-015 | Services | Création de visuels et supports | PAPI-012 |
| PAPI-016 | Services | Présentations et documents professionnels | PAPI-012 |
| PAPI-017 | Services | Recherche documentaire et synthèse | PAPI-012 |
| PAPI-018 | Services | Analyse approfondie de documents | PAPI-012 |
| PAPI-019 | Services | Contrôle qualité des livrables clients | PAPI-005 |
| PAPI-020 | Market | Responsable catalogue et offre produits | PAPI-002 |
| PAPI-021 | Market | Sourcing et vérification fournisseurs | PAPI-020 |
| PAPI-022 | Market | Analyse prix, coûts et marges | PAPI-020 |
| PAPI-023 | Market | Gestion catalogue et fiches produits | PAPI-020 |
| PAPI-024 | Market | Gestion commandes et suivi de statut | PAPI-020 |
| PAPI-025 | Market | Service client et demandes produits | PAPI-020 |
| PAPI-026 | Market | Retours, réclamations et satisfaction | PAPI-020 |
| PAPI-027 | Dropshipping | Responsable opérations dropshipping | PAPI-002 |
| PAPI-028 | Dropshipping | Validation fournisseur et fiabilité | PAPI-027 |
| PAPI-029 | Dropshipping | Calculateur coûts, marge et trésorerie | PAPI-027 |
| PAPI-030 | Dropshipping | Suivi commandes et délais logistiques | PAPI-027 |
| PAPI-031 | Dropshipping | Support client et gestion des incidents | PAPI-027 |
| PAPI-032 | Affiliation | Responsable programmes et conformité affiliation | PAPI-002 |
| PAPI-033 | Affiliation | Recherche et vérification des programmes | PAPI-032 |
| PAPI-034 | Affiliation | Stratégie contenus et campagnes affiliées | PAPI-032 |
| PAPI-035 | Affiliation | Suivi conversions et rapprochement commissions | PAPI-032 |
| PAPI-036 | Business Partners | Responsable partenariats et apport d'affaires | PAPI-002 |
| PAPI-037 | Business Partners | Prospection entreprises et qualification B2B | PAPI-036 |
| PAPI-038 | Business Partners | Gestion des partenaires et suivi des leads | PAPI-036 |
| PAPI-039 | Business Partners | Analyse des offres, commissions et accords | PAPI-036 |
| PAPI-040 | Community & Marketing | Responsable communication et communauté | PAPI-002 |
| PAPI-041 | Community & Marketing | Gestion communauté et modération | PAPI-040 |
| PAPI-042 | Community & Marketing | Réseaux sociaux et calendrier éditorial | PAPI-040 |
| PAPI-043 | Community & Marketing | Direction créative et identité visuelle | PAPI-040 |
| PAPI-044 | Community & Marketing | Prospection e-mail et suivi CRM | PAPI-036 |
| PAPI-045 | Finance, risques & administration | Responsable finance et administration | PAPI-002 |
| PAPI-046 | Finance, risques & administration | Comptabilité, rapprochement et preuves | PAPI-045 |
| PAPI-047 | Finance, risques & administration | Risques, conformité et contrôle des permissions | PAPI-005 |
| PAPI-048 | Tech & automatisation | Responsable architecture technique | PAPI-004 |
| PAPI-049 | Tech & automatisation | Fiabilité, surveillance et gestion incidents | PAPI-048 |
| PAPI-050 | Tech & automatisation | Automatisation, intégrations et outillage | PAPI-048 |

## Fiche obligatoire pour chaque poste
Avant toute activation, compléter :
- nom d'usage et nom complet validés par contrôle global d'unicité ;
- identifiant, département, équipe et responsable ;
- mission, périmètre, livrables et compétences ;
- objectifs/KPI avec méthode de mesure ;
- outils et dépendances, en privilégiant les solutions gratuites ;
- niveau d'autonomie, permissions positives et interdictions ;
- données accessibles, confidentialité et conservation ;
- date de création, statut, évaluations et historique des affectations.

## Statuts normalisés
- `planned` : poste prévu, non construit.
- `documented` : fiche complète, non implémentée.
- `prototype` : prototype construit en environnement contrôlé.
- `tested` : tests documentés et réussis.
- `approved` : validations requises obtenues.
- `deployed` : version déployée dans un environnement identifié.
- `operational` : fonctionnement vérifié par preuves récentes.
- `suspended` / `retired` : suspendu ou retiré.

Un statut ne peut pas être sauté sans preuve. La présence dans ce registre ne confère aucun accès, aucune permission et aucune autonomie.

## Contrôles de gouvernance
- Budget autorisé actuel : 0 XOF ; toute dépense ou dépendance payante reste bloquée sans autorisation explicite.
- Aucun agent ne peut envoyer de message externe, publier, contracter, acheter, retirer ou transférer des fonds sans autorisation explicite.
- Aucun secret ou identifiant d'accès n'est stocké dans ce registre.
- Les collisions historiques (notamment Awa/Awa, Malik/Malick, ainsi que les prénoms réutilisés dans plusieurs pôles de l'organigramme) doivent être résolues par un audit global avant attribution des noms et activation.
- Le registre JSON associé est la représentation machine lisible ; toute modification doit préserver l'unicité des IDs et la règle de nommage.

## État initial
Les 50 postes sont planifiés. Les noms humains restent à attribuer ou à valider après audit global des identités historiques. Aucun de ces 50 postes n'est déclaré actif, connecté ou déployé par ce document.
