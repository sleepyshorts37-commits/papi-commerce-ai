# Mission 84 — Comparaison des cinq concepts pilotes

## Objectif
Comparer les cinq concepts PAPI KIDS avec des données de niche validées par le protocole Mission 83. Le moteur ne collecte pas lui-même les données Amazon et ne crée pas de faux résultats.

## Concepts
- PKP-0001 — Nia et la rivière aux mille reflets
- PKP-0002 — Le marché des nombres de Sami
- PKP-0003 — Le petit atlas de mes émotions
- PKP-0004 — Les missions futées de la savane
- PKP-0005 — Jardins de formes : mon grand coloriage

## Méthode
Pour chaque concept, fournir une recherche indépendante avec 10 à 20 livres concurrents et toutes les preuves exigées par Mission 83. Les cinq recherches doivent porter sur des mots-clés distincts dans un même marché, pays et langue. Le classement compte simplement le nombre de signaux satisfaits parmi les trois heuristiques (0 à 3), puis départage les égalités par identifiant. Aucun poids caché, aucun volume de ventes ou bénéfice estimé.

Un score de 3/3 signifie seulement « à examiner en priorité ». Tous les résultats restent HUMAN_REVIEW_REQUIRED. Le classement ne prédit ni ventes ni rentabilité. La qualité, la différenciation, les sous-catégories, les prix et les tendances restent à examiner par une personne.

## Exécution
`PYTHONPATH=runtime python -m papi_core kids-pilot-compare chemin/vers/portfolio.json`

Le JSON doit contenir exactement les cinq concepts et cinq objets `niche_evidence` conformes au schéma Mission 83. Sans collecte vérifiée, aucun rapport comparatif réel ne peut être produit.

## État initial
Le catalogue PAPI KIDS est vide et aucune étude réelle des cinq niches n'a été collectée. Cette mission livre l'outil et le protocole, pas un classement commercial fictif.
