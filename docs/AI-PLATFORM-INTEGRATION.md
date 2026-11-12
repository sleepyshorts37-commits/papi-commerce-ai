# Plan d'intégration de la plateforme IA

**Statut : conception préparatoire — aucune dépendance externe ajoutée, aucun service connecté, aucun agent activé.**

## Décision d'architecture

Le dépôt possède déjà un noyau Python, une file d'exécution contrôlée, un worker désactivé par défaut, un planificateur déterministe, un adaptateur Supabase et des garde-fous financiers et de communication. Les nouveaux outils doivent se brancher sur ces interfaces plutôt que remplacer le noyau ou créer une deuxième source de vérité.

### Socle retenu

| Projet | Rôle cible | Décision |
|---|---|---|
| Supabase | Persistance partagée PostgreSQL, identité et audit | Réutiliser l'adaptateur et le schéma existants ; valider sur projet de test avant production. |
| LangGraph | Orchestration d'agents avec états, reprises et validation humaine | Prototype isolé derrière une interface d'orchestration ; ne pas contourner la machine à états et les permissions PAPI. |
| LiteLLM | Passerelle multi-fournisseurs de modèles | Ajouter seulement après définition des budgets, limites, journalisation et politique de données. |
| Langfuse | Traçabilité des appels IA, latence, qualité et coûts | Instrumentation facultative ; masquer les données personnelles et secrets avant export. |
| n8n | Intégrations et automatisations externes | Utiliser des webhooks signés et des identifiants idempotents ; aucun workflow ne peut débloquer une action interdite. |

### Outils évalués mais non retenus dans le socle initial

- CrewAI : chevauchement fonctionnel avec LangGraph ; réévaluer uniquement si un besoin concret de coordination d'équipes le justifie.
- Microsoft AutoGen : expérimentation possible, mais ne pas maintenir deux moteurs d'agents en production sans avantage mesuré.
- Dify : intéressant pour prototyper des applications IA et interfaces métier ; ne doit pas devenir un second registre des agents ou des permissions.
- Browser Use : capacité à risque élevé ; isoler le navigateur, limiter les domaines et exiger une approbation avant toute action externe.
- Open WebUI : interface facultative ; ne pas exposer les outils d'administration ni les secrets.

## Architecture cible

1. **PAPI Core reste l'autorité** pour les identités, permissions, états de mission, approbations, audit et comptabilité.
2. **LangGraph** pourra appeler le noyau via des adaptateurs typés ; il ne stockera pas une autorité parallèle.
3. **LiteLLM** pourra fournir une interface commune aux modèles, avec liste de fournisseurs autorisés, plafond de dépenses et arrêt en cas de dépassement.
4. **Langfuse** recevra des traces expurgées : identifiants techniques, durée, modèle, compteurs et statut, jamais de mots de passe, OTP, clés, CVV ou contenu sensible non nécessaire.
5. **n8n** pourra déclencher des événements métier limités. Chaque événement devra être authentifié, validé, dédupliqué et soumis aux permissions PAPI.
6. **Supabase** sera la persistance partagée après tests de sécurité et d'intégration. Les clés serveur resteront exclusivement dans un gestionnaire de secrets.

## Phases d'implémentation

### Phase A — Inventaire et contrats
- Cartographier les interfaces existantes du noyau et les tests.
- Définir des contrats d'adaptateur indépendants des fournisseurs.
- Fixer les versions et licences des projets retenus.
- Définir les données autorisées à quitter l'environnement PAPI.

### Phase B — Prototype local sans effet externe
- Prototyper un seul workflow LangGraph sur des données fictives.
- Tester les interruptions, reprises, erreurs, validations humaines et idempotence.
- Comparer le prototype aux capacités du noyau actuel.
- Aucun compte fournisseur, coût API, webhook public ou agent autonome.

### Phase C — Observabilité et modèle
- Ajouter une couche LiteLLM uniquement avec budget nul par défaut et fournisseur explicitement autorisé.
- Ajouter Langfuse avec expurgation et rétention définie.
- Tester les plafonds, erreurs fournisseur, indisponibilité et arrêt d'urgence.

### Phase D — Automatisations contrôlées
- Évaluer n8n dans un environnement isolé.
- Commencer par des événements internes non sensibles et des notifications de test.
- Signer les webhooks, vérifier les signatures, appliquer anti-rejeu et idempotence.
- Garder les messages externes, publications, achats et paiements désactivés.

### Phase E — Validation avant production
- Tests unitaires, intégration, concurrence, reprise après crash et restauration.
- Revue indépendante de sécurité et test d'intrusion.
- Vérification des licences, conditions d'utilisation, coûts, quotas et hébergement.
- Approbation explicite du propriétaire pour chaque service payant et chaque activation de production.

## Critères de réussite

- Aucun contournement de la politique centrale ou de la machine à états.
- Toutes les exécutions possèdent un identifiant, un acteur, un statut et une trace d'audit.
- Les reprises sont idempotentes et ne créent pas de doublons métier.
- Les coûts sont plafonnés et visibles ; arrêt automatique en cas de dépassement.
- Les secrets et données personnelles sont absents des journaux et traces.
- Le mode par défaut reste inactif : aucune prospection, publication, dépense, transaction ou communication externe automatique.

## Références officielles des projets

- LangGraph : https://github.com/langchain-ai/langgraph
- Supabase : https://github.com/supabase/supabase
- LiteLLM : https://github.com/BerriAI/litellm
- Langfuse : https://github.com/langfuse/langfuse
- n8n : https://github.com/n8n-io/n8n
- CrewAI : https://github.com/crewAIInc/crewAI
- AutoGen : https://github.com/microsoft/autogen
- Dify : https://github.com/langgenius/dify
- Browser Use : https://github.com/browser-use/browser-use
- Open WebUI : https://github.com/open-webui/open-webui
