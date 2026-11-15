# Mission 119 — Orchestrateur PAPI KIDS PKP-0001

## Implémentation
- Ajout de `runtime/papi_core/papi_kids_orchestrator.py`.
- Lecture des 24 scènes du brief Markdown et vérification stricte de la numérotation.
- Injection de la bible graphique dans chaque prompt pour préserver la continuité.
- Création d'une campagne déterministe PKP-0001 par le planificateur existant, avec lots bornés et unités de quota.
- Conservation des empreintes SHA-256 des sources pour identifier les versions de bible et de prompts.

## Garde-fous
- La préparation est hors ligne et n'appelle aucun fournisseur.
- Le quota gratuit doit être explicitement confirmé au moment de préparer ET d'exécuter.
- L'exécution exige une autorisation explicite, un plafond de dépense égal à zéro et un routeur dont chaque modèle déclare `free_confirmed=True`.
- Aucun fallback payant ni nouvelle tentative automatique n'est introduit.
- Les lots sont bornés et reprenables via le moteur/campagne existants.
- Les assets restent en attente de revue ; aucune validation visuelle humaine n'est simulée.

## Tests
Tests unitaires prévus avec faux fournisseurs : 24 pages, stabilité, quota non confirmé, scène manquante, autorisation absente, plafond non nul et adaptateur non vérifié. Aucun appel réseau, aucune clé API, aucune dépense.

## Limites
Le code prépare un plan réel exploitable mais ne génère pas d'illustrations dans cette mission. La vérification du caractère gratuit d'un quota dépend de preuves et de paramètres fiables fournis par l'application ; un booléen de configuration seul ne prouve pas les conditions tarifaires du fournisseur. Avant activation, connecter une source de quota fiable et persistante, puis effectuer des images tests sous approbation humaine.
