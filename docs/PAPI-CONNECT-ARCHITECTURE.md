# Mission 182 — PAPI CONNECT : architecture et réutilisation open source

## Objectif
Construire une couche commune d'intégrations pour PAPI COMMERCE AI en réutilisant des projets open source et des API officielles, sans multiplier les intégrations directes dans chaque agent.

## État initial vérifié
- Le dépôt possède déjà un noyau Python, un worker désactivé par défaut, des permissions, un audit et des adaptateurs de stockage local/Supabase.
- `requirements.txt` contient actuellement `cryptography` et `reportlab` ; aucune dépendance d'agent ou de fournisseur LLM n'est déclarée ici.
- Le README et la documentation indiquent qu'aucun fournisseur IA réel, environnement Supabase distant ou worker permanent n'est actuellement connecté.
- Les PR #355 à #358 constituent une chaîne de travail ouverte et non fusionnée sur PAPI CONNECT.

## Principes obligatoires
1. Budget par défaut : 0 FCFA. Aucun essai payant, abonnement, crédit API, hébergement payant ou dépassement de quota sans accord explicite du propriétaire.
2. Aucun secret dans Git, les prompts, les issues, les logs ou les réponses d'agent. Secrets uniquement dans l'environnement serveur ou un coffre adapté.
3. Toute intégration est désactivée par défaut et doit déclarer fournisseur, endpoint, région, conditions d'utilisation, données transmises, quotas, coûts potentiels, permissions et procédure de révocation.
4. Un fournisseur annoncé « gratuit » doit être vérifié à la date de l'activation : les offres, limites, disponibilité géographique et droits commerciaux peuvent changer.
5. Aucun agent ne peut contourner une limite, un CAPTCHA, une restriction de plateforme ou un refus d'autorisation en basculant vers un autre fournisseur.
6. Une intégration n'est « opérationnelle » qu'après test reproductible avec credentials de test, contrôle des erreurs, limites de débit et preuve d'exécution.
7. Les agents ne reçoivent que les outils nécessaires à leur rôle ; les actions externes, financières, de publication et de contact restent soumises aux permissions existantes.

## Architecture cible

```
Agents spécialisés
       |
PAPI TOOLBOX — catalogue d'outils et permissions par agent
       |
PAPI CONNECT — contrats/adaptateurs communs
       |
+----------------+----------------+----------------+
| Fournisseurs IA| Recherche/API  | Documents/Media|
+----------------+----------------+----------------+
       |
PAPI API MANAGER — secrets côté serveur, quotas, budget, rate limits
       |
PAPI MONITOR — disponibilité, latence, erreurs, coûts et audit
       |
PAPI FALLBACK — alternative autorisée, même politique et mêmes limites
```

Le registre des fournisseurs est une source de configuration et de gouvernance, pas un coffre à secrets. Il stocke des noms de variables d'environnement, jamais leurs valeurs.

## Projets open source à réutiliser ou évaluer

| Projet | Usage envisagé | Décision initiale |
|---|---|---|
| https://github.com/n8n-io/n8n | Workflows d'automatisation et connecteurs | Évaluer en phase ultérieure ; auto-hébergement implique serveur, maintenance et sécurité |
| https://github.com/BerriAI/litellm | Passerelle multi-fournisseurs LLM, routage et budgets | Évaluer comme passerelle optionnelle ; ne pas l'ajouter au runtime avant preuve de besoin |
| https://github.com/langfuse/langfuse | Traces, coûts, latence et observabilité LLM | Évaluer ; auto-hébergement et collecte de données à examiner |
| https://github.com/supabase/supabase-py | Client Python officiel Supabase | Réutiliser seulement pour l'adaptateur Supabase déjà prévu, après tests d'intégration |
| https://github.com/modelcontextprotocol/python-sdk | Exposer/consommer des outils via MCP | Évaluer pour standardiser les outils ; permission par outil obligatoire |
| https://github.com/googleapis/python-genai | SDK Python officiel Gemini | Candidat au premier adaptateur IA, sous réserve de vérifier quota gratuit, région Sénégal, données et conditions au moment de l'activation |

Ces projets sont des candidats techniques, pas des services déjà installés ou connectés. L'utilisation de leur code n'accorde pas automatiquement l'accès aux API hébergées par leurs éditeurs.

## Contrat minimal d'un fournisseur

Chaque adaptateur doit exposer :
- identifiant stable et version ;
- capacités prises en charge ;
- variables de configuration requises (noms uniquement) ;
- plafond de coût explicite et quota local ;
- délais maximum, retries bornés et idempotence si applicable ;
- classification des données et politique de conservation ;
- vérification de santé non destructive ;
- erreurs normalisées : indisponible, quota dépassé, authentification, refus, coût interdit ;
- tests unitaires avec faux fournisseur et tests d'intégration activés uniquement par opt-in.

## Registre initial des fournisseurs

Statut initial de chaque entrée : `proposed` (non activée).

| ID | Capacité | Fournisseur candidat | Statut | Condition avant activation |
|---|---|---|---|---|
| llm.gemini | Génération/analyse de texte | Gemini API | proposed | Vérifier offre, quota, Sénégal, confidentialité et coûts |
| llm.local | Modèle local | Ollama / llama.cpp | proposed | Mesurer ressources nécessaires ; aucune facture API mais coût matériel/électricité |
| automation.n8n | Workflows | n8n auto-hébergé | proposed | Hébergement, mises à jour, sécurité et disponibilité |
| observability.langfuse | Traces LLM | Langfuse | proposed | Choisir cloud ou auto-hébergement et politique de données |
| storage.supabase | Base et stockage | Supabase | proposed | Projet de test, RLS, secrets serveur, sauvegardes |
| tools.mcp | Outils standardisés | MCP Python SDK | proposed | Liste blanche de serveurs et outils, isolation et permissions |

Aucune clé API ni URL privée ne doit figurer dans ce registre.

## Plan d'implémentation progressif

1. Mission 182 : architecture, règles, inventaire des projets et contrats.
2. Mission 183 : schéma validé du registre des fournisseurs, capacités, quotas, permissions et statuts.
3. Mission 184 : interfaces d'adaptateurs et fournisseur simulé ; tests sans réseau.
4. Mission 185 : fiabilisation de la frontière adaptateur, erreurs normalisées et refus des retries automatiques ambigus.
5. Mission 186 : observabilité locale, agrégats d'utilisation et coûts indicatifs, sans fournisseur réel.
6. Mission 187 : attribution des outils à deux agents pilotes avec permissions minimales, après revue de sécurité et autorisation explicite.
7. Mission 188 : premier fournisseur réel uniquement après sélection, vérification des conditions, coûts, quotas, disponibilité au Sénégal, confidentialité et autorisation explicite du propriétaire.
8. Missions suivantes : observabilité partagée, limites de consommation, fallback et extension des fournisseurs.

## Critères d'acceptation
- Architecture documentée sans prétendre qu'un service est connecté.
- Dépendances externes identifiées avec leurs responsabilités et risques.
- Aucune nouvelle dépendance runtime installée sans usage concret et validation de licence/maintenance.
- Aucun secret ajouté au dépôt.
- Aucun compte créé, aucun service distant appelé, aucune dépense, aucun agent activé.
- Les missions distinguent clairement simulation, test d'intégration et production.
