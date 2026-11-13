# Cycle PAPI — génération de contenus commerciaux (5 jours)

## Objectif
Ajouter un générateur déterministe de brouillons commerciaux, fondé exclusivement sur les informations fournies. Aucun modèle externe, appel réseau, publication ou contact client n'est activé.

## Jour 1 — Cadrage et contrat
- [x] Définir les types de contenus et secteurs pris en charge.
- [x] Définir le schéma strict du brief et les limites de taille.
- [x] Définir la politique « faits fournis uniquement » et revue humaine obligatoire.

## Jour 2 — Moteur de génération
- [x] Générer fiches produits, présentations de services, pages établissement et publications.
- [x] Adapter le ton et les mentions de prudence selon le secteur.
- [x] Produire une sortie structurée réutilisable.

## Jour 3 — Sécurité et garde-fous
- [x] Refuser les champs inconnus, balisages, briefs malformés et textes trop longs.
- [x] Refuser les allégations explicites de guérison, efficacité ou résultats garantis non vérifiés.
- [x] Refuser les dosages dans les contenus de pharmacie.
- [x] Marquer chaque brouillon comme nécessitant une revue humaine.

## Jour 4 — Tests et intégration
- [x] Ajouter des tests couvrant 4 types de contenu et 5 secteurs.
- [x] Tester les limites et garde-fous pharmacie.
- [ ] Vérifier les workflows CI GitHub sur la branche.

## Jour 5 — Documentation et livraison
- [x] Documenter le contrat d'entrée, la sortie et les limites.
- [ ] Mettre à jour README et roadmap.
- [ ] Ouvrir une pull request et vérifier les contrôles CI.

## Critères de sortie
Génération locale déterministe, aucun fait non sourcé, revue humaine obligatoire, tests automatisés et CI observée.