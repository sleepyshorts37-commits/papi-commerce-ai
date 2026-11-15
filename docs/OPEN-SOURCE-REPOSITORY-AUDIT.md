# Audit des dépôts open source pour PAPI COMMERCE AI

Date de vérification : 2026-11-15  
Branche de référence : `mission-102-free-quota-provider-routing`  
Objectif : sélectionner des composants réutilisables sans introduire de coûts obligatoires, de dépendances non licenciées ou de doublons architecturaux.

## Résumé exécutif

Décision : **ne pas importer un framework complet immédiatement**. PAPI possède déjà un noyau Python, une file d'exécution, des identités d'agents, des permissions, des contrôles d'approbation et des tests. Les dépôts externes doivent être évalués comme briques ciblées et intégrés derrière des interfaces internes.

Ordre de priorité :
1. LangGraph : étudier comme modèle de workflows durables et reprise sur erreur ; ne pas remplacer le worker existant sans preuve de gain.
2. Agent Squad : étudier les patterns de routage multi-agents ; éviter d'ajouter un second orchestrateur en parallèle.
3. Cloudflare Workers AI / cf-image-gen : utiliser l'API officielle et notre propre adaptateur FREE_ONLY ; le dépôt cf-image-gen est seulement un exemple de démarrage.
4. ComfyUI : option de génération auto-hébergée ou serveur GPU séparé, pas un fournisseur cloud gratuit garanti.
5. n8n : éventuellement comme outil d'intégration externe isolé, après revue de licence et des coûts d'hébergement.

## Dépôts vérifiés

Les métadonnées GitHub ont été consultées le 15 novembre 2026. Les étoiles et dates de push sont des indicateurs de contexte, pas une preuve de qualité ou de sécurité.

| Dépôt | Licence déclarée | Activité observée | Décision |
|---|---|---|---|
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | MIT | Non archivé ; push récent ; projet Python mature | **À étudier en priorité** pour workflows, états et reprise. Dépendances et coût des modèles séparés. |
| [2FastLabs/agent-squad](https://github.com/2FastLabs/agent-squad) | Apache-2.0 | Non archivé ; push récent ; Python | **À étudier** pour routage et délégation. Ne pas superposer à notre orchestrateur sans prototype comparatif. |
| [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) | GPL-3.0 | Non archivé ; très actif ; Python | **Option image séparée**. GPU, stockage des modèles et hébergement restent à fournir. Revue GPL-3.0 nécessaire avant redistribution ou intégration dérivée. |
| [ai-dock/comfyui-api-wrapper](https://github.com/ai-dock/comfyui-api-wrapper) | Aucune licence détectée dans les métadonnées consultées | Dernier push observé : 2026-05-08 | **Ne pas copier ni redistribuer** tant que l'auteur n'a pas clarifié la licence. Peu d'activité récente. |
| [n8n-io/n8n](https://github.com/n8n-io/n8n) | NOASSERTION dans GitHub ; projet fair-code | Très actif ; TypeScript | **Option conditionnelle** pour automatisations. Ce n'est pas une licence open source OSI classique ; vérifier les conditions Sustainable Use avant usage SaaS/commercial. L'auto-hébergement a un coût d'infrastructure. |
| [ErbaZZ/cf-image-gen](https://github.com/ErbaZZ/cf-image-gen) | MIT | Non archivé ; petit projet ; dernier push observé 2026-05-17 | **Référence pédagogique uniquement**. Faible adoption ; vérifier le code et les modèles avant toute reprise. Notre adaptateur doit suivre la documentation Cloudflare officielle. |
| [sass-maker/free-ai](https://github.com/sass-maker/free-ai) | MIT | Petit projet ; push observé 2026-11-13 | **À auditer davantage, pas à intégrer maintenant**. La promesse de routage gratuit ne crée aucun quota fournisseur et ne garantit pas la disponibilité ni la conformité des modèles. |
| [IO-AtelierTech/comfyui-mcp](https://github.com/IO-AtelierTech/comfyui-mcp) | MIT | Petit projet ; dernier push observé 2025-12-28 | **Option expérimentale** pour piloter ComfyUI via MCP ; maintenance à vérifier. |

## Architecture d'intégration retenue

### 1. Conserver le noyau PAPI

Le dépôt contient déjà :
- `runtime/papi_core/worker.py`, `worker_store.py` et les adaptateurs de stockage ;
- identités, permissions, file d'exécution et contrôles d'approbation ;
- tests unitaires du worker, des permissions, de la file et du stockage ;
- une politique `safe_scaffold` avec exécution et actions externes désactivées.

Il serait risqué de remplacer ces fondations par une bibliothèque externe sans tests de non-régression.

### 2. Définir des ports internes

Créer des interfaces PAPI stables avant de connecter des frameworks :
- `AgentWorkflowPort` : entrée, état, reprise, résultat et journal d'exécution ;
- `ImageProviderPort` : génération d'image, modèle, format, erreurs et identifiant fournisseur ;
- `QuotaLedgerPort` : réservation, confirmation, libération et fenêtre de renouvellement ;
- `AutomationPort` : déclenchement d'un workflow externe avec permissions minimales.

Les bibliothèques tierces restent derrière ces interfaces. Les données non fiables provenant des modèles et fournisseurs ne peuvent jamais modifier les permissions.

### 3. Règles FREE_ONLY obligatoires

- Refuser tout modèle ou fournisseur dont le coût n'est pas explicitement connu comme nul dans le cadre du compte configuré.
- Ne jamais traiter « open source » comme synonyme de « hébergement gratuit ».
- Ne jamais traiter une passerelle « free tier » comme une garantie de quota.
- Réserver le quota avant l'appel, confirmer la consommation après réponse et libérer la réservation en cas d'échec certain.
- En cas de timeout ambigu, conserver une réservation prudente jusqu'à réconciliation afin d'éviter le double dépassement.
- Aucun fallback payant, aucun achat automatique de crédits, aucune clé dans Git.
- Vérifier séparément les droits commerciaux des modèles, poids, sorties et jeux de données.

## Risques et points de décision

1. **GPU** : ComfyUI ne rend pas le GPU gratuit. Le matériel actuel de l'utilisateur ne doit pas être supposé capable d'exécuter confortablement des modèles de diffusion.
2. **Quotas cloud** : les quotas sont définis par fournisseur, compte, modèle et période ; ils peuvent changer. Le registre local PAPI n'est qu'une estimation tant qu'il n'est pas réconcilié avec une source officielle.
3. **Licences** : MIT et Apache-2.0 sont généralement permissives avec obligations de conservation des notices ; GPL-3.0 et fair-code nécessitent une revue d'usage/distribution ; l'absence de licence ne donne pas de droit de réutilisation.
4. **Sécurité** : auditer dépendances, permissions, appels réseau, télémétrie, gestion des secrets et mises à jour avant toute intégration.
5. **Confidentialité** : ne pas envoyer de données clients à un fournisseur tiers sans base légale, information et autorisation adaptées.

## Plan d'intégration proposé

- Étape A : établir les contrats Python internes et leurs tests unitaires.
- Étape B : réaliser un prototype isolé LangGraph comparé au worker PAPI actuel sur les mêmes scénarios.
- Étape C : développer l'adaptateur Cloudflare Workers AI avec client injectable et mocks ; aucune clé ni requête réelle dans les tests.
- Étape D : développer un ledger de quotas avec réservation/commit/release et protection contre dépassement concurrent.
- Étape E : connecter ComfyUI uniquement si un serveur GPU autorisé et sans coût obligatoire est disponible.
- Étape F : évaluer n8n uniquement pour les intégrations où les règles de licence et d'hébergement conviennent.

## Sources

- https://github.com/langchain-ai/langgraph
- https://github.com/2FastLabs/agent-squad
- https://github.com/Comfy-Org/ComfyUI
- https://github.com/ai-dock/comfyui-api-wrapper
- https://github.com/n8n-io/n8n
- https://github.com/ErbaZZ/cf-image-gen
- https://github.com/sass-maker/free-ai
- https://github.com/IO-AtelierTech/comfyui-mcp
- Cloudflare Workers AI : https://developers.cloudflare.com/workers-ai/
- n8n licence : https://github.com/n8n-io/n8n/blob/master/LICENSE.md

## Limites de cet audit

Audit de métadonnées GitHub et de l'architecture PAPI ; il ne constitue pas un audit de sécurité ligne par ligne, une validation juridique ni un test de performance. Aucun dépôt externe n'a été cloné, installé, exécuté ou copié. Aucun service, compte ou agent n'a été activé.
