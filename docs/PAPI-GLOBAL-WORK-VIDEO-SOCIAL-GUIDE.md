# Guide — GLOBAL WORK, SOCIAL GROWTH et VIDEO TASKS

## 1. PAPI GLOBAL WORK

Le module \`papi_core.global_work\` valide et évalue une opportunité saisie à partir d'une source publique. Il ne recherche pas lui-même sur Internet et ne soumet aucune candidature.

Champs principaux :
- \`source_url\`, \`title\`, \`description\) : provenance et description ;
- \`country_eligibility\`, \`eligible_countries\) : pays autorisés ;
- \`compensation_amount\`, \`currency\), \`estimated_minutes\) : rémunération et durée ;
- \`upfront_cost\) : coût à avancer ;
- \`automation_policy\), \`ai_policy\) : conditions de la plateforme ;
- \`human_presence_required\) : présence humaine requise ;
- \`payout_methods\) : moyens de paiement proposés.

Exemple d'utilisation :

\`\`\`python
from papi_core.global_work import evaluate_opportunity

result = evaluate_opportunity(
    opportunity,
    owner_country="SN",
    accepted_payout_methods=("PayPal",),
    require_zero_upfront_cost=True,
)
\`\`\`

Décisions possibles :
- \`reject\) : incompatibilité explicite avec la politique ou exigence humaine ;
- \`manual_review\) : information manquante ou condition à vérifier ;
- \`candidate_for_owner_policy_review\) : candidate à une validation supplémentaire, sans autorisation de candidature.

Le résultat indique toujours \`application_submitted=False\). Une candidate n'est ni un contrat gagné ni un revenu.

## 2. PAPI SOCIAL GROWTH

Le registre \`data/social-growth.json\` définit cinq agents initiaux :
- TikTok ;
- Instagram ;
- Facebook ;
- YouTube ;
- LinkedIn.

Chaque agent cumule les responsabilités suivantes :
1. créer et publier des contenus adaptés au réseau, lorsque l'accès et l'autorisation le permettent ;
2. promouvoir la page et développer une audience réelle ;
3. répondre aux interactions dans les limites autorisées ;
4. rechercher des clients et des missions rémunérées ;
5. promouvoir les produits de PAPI et contribuer aux ventes ;
6. suivre les prospects, conversions et revenus vérifiés.

Le responsable SOCIAL GROWTH compare les résultats des plateformes. Les métriques de portée et d'abonnés ne doivent jamais être confondues avec des ventes ou des revenus.

## 3. PAPI VIDEO TASKS

Le module \`papi_core.video_tasks\` accepte des liens HTTPS YouTube reconnus :
- \`youtube.com/watch?v=...\` ;
- \`youtu.be/...\` ;
- \`youtube.com/shorts/...\` ;
- \`youtube.com/embed/...\` ;
- \`youtube.com/live/...\`.

\`create_video_task\` crée une tâche et dix sous-tâches d'analyse. Les agents ont des angles distincts : structure, faits clés, enseignements, chronologie, exemples, technique, langue, pédagogie, vérification des affirmations et synthèse.

Exemple :

\`\`\`python
from papi_core.video_tasks import create_video_task, build_video_report

task = create_video_task(
    task_id="video-001",
    url="https://www.youtube.com/watch?v=abcdefghijk",
    submitted_by="owner",
    created_at="2026-11-13T22:00:00Z",
)
report = build_video_report(task)
\`\`\`

La tâche est une structure locale d'intake et de distribution. Elle ne lit pas encore la vidéo, ne lance pas de navigateur et ne récupère pas automatiquement les sous-titres. Ces intégrations nécessiteront un connecteur autorisé, une gestion des droits et une validation distincte.

## 4. Limites opérationnelles

Ce cycle fournit des schémas, validateurs, évaluateurs et tâches locales. Il n'active pas :
- le scraping ou la navigation automatique sur les plateformes ;
- l'envoi de candidatures ;
- la publication ou la messagerie externe ;
- le visionnage automatisé ou la lecture répétée ;
- l'extraction de transcriptions depuis des sources non autorisées ;
- les paiements, retraits, transferts ou dépenses ;
- les workers permanents ou le fonctionnement 24 h/24.

Les intégrations réelles seront ajoutées après vérification des API, des conditions des plateformes, des droits d'accès, des coûts et des permissions.
