# Intégration génération commerciale → PAPI WEB BUILDER (5 jours)

## Objectif
Relier le moteur de contenus commerciaux déterministes au constructeur de sites statiques afin de produire un premier site vitrine cohérent à partir d'un brief validé.

## Jour 1 — Contrats et dépendances
- Réutiliser les validateurs de contenus, d'architecture et de site.
- Définir le contrat d'entrée/sortie et les limites de taille.
- Maintenir une génération locale, sans réseau ni modèle externe.

## Jour 2 — Pipeline d'intégration
- Ajouter `papi_core.commercial_site`.
- Transformer les contenus validés en brief du WEB BUILDER.
- Refuser les contenus trop longs plutôt que les tronquer silencieusement.

## Jour 3 — Sécurité et qualité
- Réutiliser l'échappement HTML et les contrôles du constructeur.
- Préserver les interdictions d'allégations non vérifiées et de dosages pharmaceutiques.
- Garder la revue humaine obligatoire et la publication désactivée.

## Jour 4 — Tests
- Couvrir génération nominale, échappement, longueur, réutilisation de projet, refus d'allégations et dosages.
- Vérifier le rapport qualité du site statique.

## Jour 5 — Documentation et validation
- Documenter le flux, les limites et les commandes.
- Exécuter la CI GitHub et corriger les régressions détectées.
- Ouvrir une PR ; aucune fusion ni publication sans validation distincte.

## Critères d'acceptation
- Le site est généré localement avec les faits fournis.
- Le rapport qualité intégré est positif.
- Aucune requête réseau, publication ou transaction.
- Toute sortie reste soumise à validation humaine.
