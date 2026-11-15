# Mission 101 — Préparer PAPI IMAGE FACTORY en mode FREE_ONLY

Date : 2026-11-15
Base : Mission 28, commit `c7d04eafff9ba2761fc36d021af56d1b3e1f4c35`.
CI observée sur ce SHA : workflow `PAPI core tests`, run 984, conclusion `success`.

## Vérification de l'existant
La PR #188 (Mission 28) fournit le moteur de workers : registre d'identité, compétences, permissions, capacité, affectation idempotente, bail/fencing et complétion contrôlée. Elle reste ouverte et en brouillon ; aucune fusion ni activation n'est constatée. La CI du SHA c7d04e... est réussie.

Le moteur de workers ne fournit pas encore les adaptateurs de génération d'image ni un exécuteur de fournisseur. Les missions graphiques PKP-0001 ont montré qu'une simple génération d'image sans contrôle de continuité ne suffit pas.

## Recherche des options gratuites
- Google AI Studio : gratuit pour certains usages/regions, mais les modèles image via API ne sont pas tous couverts par un quota gratuit. Ne pas assimiler UI gratuite et API image gratuite.
- Hugging Face Inference Providers : documentation actuelle indique pas de crédits mensuels inclus pour les comptes Free ; les crédits doivent être achetés.
- ComfyUI : voie open source auto-hébergée, sans frais d'API, mais demande une machine compatible et des modèles dont la licence autorise l'usage prévu.

Aucune génération via ces fournisseurs n'a été lancée et aucun compte, secret ou clé n'a été demandé ou créé.

## Livrables de la mission
- `docs/PAPI-IMAGE-FACTORY-ARCHITECTURE.md` : équipe d'agents, flux de production, contrat d'adaptateur et gouvernance.
- `docs/PAPI-IMAGE-PROVIDERS-FREE-ONLY.md` : comparaison initiale et politique de routage sans frais.

## Décisions
- Mode par défaut : `FREE_ONLY`.
- Aucun fallback payant.
- Aucun agent activé.
- Aucune clé ou secret dans le dépôt.
- Les images générées doivent passer la QA et une approbation humaine.
- Le registre de workers de Mission 28 reste un prérequis technique, mais n'est pas fusionné/activé par cette mission.

## Statut
Architecture et vérification documentaire terminées ; aucun moteur image opérationnel, aucun agent générateur activé, aucun test réel de génération automatique. Aucune dépense, publication ou effet externe.
