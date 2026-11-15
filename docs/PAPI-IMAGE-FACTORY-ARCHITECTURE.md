# PAPI IMAGE FACTORY — Architecture des agents de génération sans frais

Date : 2026-11-15
Base technique : Mission 28, worker engine, commit `c7d04eafff9ba2761fc36d021af56d1b3e1f4c35`

## Objectif
Permettre à PAPI COMMERCE AI de préparer, générer, contrôler et classer des images en privilégiant les moteurs réellement gratuits. Aucun agent ne doit pouvoir déclencher une dépense ou basculer silencieusement vers une API payante.

## Équipe spécialisée proposée
1. **PAPI ART DIRECTOR** — reçoit le brief, fixe le style, le format, les contraintes et le niveau de qualité.
2. **PAPI PROMPT ENGINEER** — transforme le brief en prompt structuré, négatif et reproductible.
3. **PAPI CHARACTER KEEPER** — vérifie les personnages, accessoires, couleurs, proportions et continuité d'une page à l'autre.
4. **PAPI IMAGE ROUTER** — choisit un fournisseur autorisé selon capacité, disponibilité, licence et coût réel.
5. **PAPI IMAGE GENERATOR** — appelle uniquement l'adaptateur autorisé et retourne les métadonnées du rendu.
6. **PAPI ART QA** — contrôle le brief, la composition, les artefacts, le texte intégré, les droits et la cohérence ; peut rejeter et demander une nouvelle tentative.
7. **PAPI ASSET LIBRARIAN** — classe les rendus, versions, prompts, modèle, licence, date et statut d'approbation.
8. **PAPI COST GUARD** — bloque toute opération payante, toute facturation et tout dépassement du budget autorisé.

## Cycle de travail
`brief_received → brief_structured → prompt_ready → provider_selected → generation_requested → generated → qa_passed | qa_rejected → approved_by_human → asset_archived`

Une image générée n'est jamais considérée comme approuvée automatiquement. Le texte ou badge « validé » rendu dans l'image n'a aucune valeur d'approbation.

## Contrat commun des fournisseurs
Chaque adaptateur expose :
- `provider_id`, `model_id`, `capabilities`, `supported_formats`, `license_reference`
- `cost_class`: `free_quota`, `self_hosted_no_api_fee`, `paid`, `unknown`
- `quota_status`, `availability_status`, `last_verified_at`
- `generate(prompt, negative_prompt, dimensions, seed?)`
- résultat : URI/asset, dimensions, modèle, paramètres, coût estimé/réel, durée, statut et erreurs normalisées.

Le routeur ne doit jamais traiter `unknown` comme gratuit.

## Politique « FREE_ONLY »
- Le mode par défaut des projets de l'utilisateur est `FREE_ONLY`.
- Les classes `paid` et `unknown` sont bloquées.
- Un quota gratuit épuisé signifie `WAIT_OR_FALLBACK`, jamais un basculement payant.
- Aucun achat de crédits, abonnement, paiement ou activation d'essai payant.
- Aucun secret/API key dans Git, les prompts, les rapports ou le navigateur client. Les secrets éventuels sont stockés uniquement dans un coffre de secrets du runtime après action explicite du propriétaire.
- Le routeur journalise le fournisseur choisi, la raison, le statut du quota et le coût (qui doit rester à zéro).
- Les licences et droits commerciaux du modèle et des images doivent être vérifiés avant usage commercial.

## Déploiement par étapes
1. Registre et contrats d'adaptateurs, sans secret et sans appel externe.
2. Adaptateur local ComfyUI, désactivé tant qu'un hôte compatible n'est pas disponible.
3. Adaptateurs cloud uniquement après vérification documentaire des conditions, quotas et licences ; aucun n'est présumé gratuit.
4. Tests de contrat avec faux fournisseur (mock) et tests de blocage du mode payant.
5. Activation individuelle, explicite et révocable par l'administrateur.

## Dépendances et limites
Le worker engine fournit l'identité, les compétences, les permissions, les affectations et les jobs internes. Il ne constitue pas à lui seul un moteur d'image : il faut ajouter les adaptateurs et un exécuteur contrôlé. Aucun worker n'est activé par cette architecture.
