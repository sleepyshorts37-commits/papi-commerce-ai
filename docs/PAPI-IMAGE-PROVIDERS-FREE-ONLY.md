# Registre initial des moteurs d'image — PAPI IMAGE FACTORY

Date de vérification documentaire : 2026-11-15
Règle : aucune promesse de génération illimitée ou gratuite. Revalider les conditions et quotas avant chaque activation.

| Option | Situation vérifiée | Décision FREE_ONLY |
|---|---|---|
| Google AI Studio / Gemini API | L'interface AI Studio peut être utilisée gratuitement dans les régions disponibles, mais la page officielle de tarification indique que certains modèles de génération d'image API n'ont pas de niveau gratuit. | Ne pas supposer que l'API image est gratuite ; bloquer tout modèle sans ligne gratuite explicite. |
| Hugging Face Inference Providers | La documentation de tarification indique que les utilisateurs gratuits n'ont pas de crédits mensuels inclus et doivent acheter des crédits pour l'usage des providers. | Exclu du mode gratuit strict, sauf changement officiel des conditions. |
| ComfyUI auto-hébergé | Logiciel open source permettant d'exécuter localement des modèles compatibles ; aucun coût d'API, mais le calcul matériel et l'électricité restent à la charge de l'hôte. | Candidat principal à long terme si un ordinateur/serveur compatible est disponible et si la licence du modèle est vérifiée. |
| Autres services hébergés | Les quotas, régions, modèles et licences varient et changent régulièrement. | En attente d'une vérification officielle par fournisseur ; aucun appel tant que le statut n'est pas établi. |

## Sources officielles consultées
- Google Gemini API pricing : https://ai.google.dev/gemini-api/docs/pricing
- Google AI Studio pricing : https://aistudio.google.com/docs/pricing
- Hugging Face Inference Providers pricing : https://huggingface.co/docs/inference-providers/en/pricing
- ComfyUI repository : https://github.com/Comfy-Org/ComfyUI

## Conséquence pratique
Le chemin le plus fiable vers un coût API nul est l'inférence auto-hébergée, mais elle n'est pas « sans coût » au sens matériel. Les agents PAPI peuvent préparer les prompts et les contrôles dès maintenant ; la génération automatique attendra un moteur dont la gratuité, la disponibilité, les licences et la capacité sont confirmées.
