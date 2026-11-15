# Mission 83 — Validation des niches Amazon KDP

## Protocole inspiré de la capture fournie
1. Concurrence maîtrisée : moins de 2 500 résultats pour le mot-clé principal.
2. Demande apparente : BSR des trois meilleurs livres de la première page inférieur à 100 000.
3. Porte d'entrée : moyenne des avis des livres échantillonnés sur la première page inférieure à 50.

Ces trois seuils sont des heuristiques de présélection, pas des règles Amazon ni des garanties de ventes. Le moteur exige 10 à 20 concurrents, leur rang, ASIN, BSR, nombre d'avis, format, URL source et date d'observation. La requête, le pays, la langue, l'URL et la date de recherche sont également obligatoires.

## Résultats
- 3 signaux : PROMISING_FOR_HUMAN_REVIEW.
- 2 signaux : REWORK_AND_RESEARCH_MORE.
- 0 ou 1 signal : WEAK_SIGNAL_STOP_OR_REPOSITION.

Même avec trois signaux positifs, la décision reste HUMAN_REVIEW_REQUIRED. Aucun GO automatique, aucun livre créé et aucune publication autorisée.

## Limites de méthode
Le nombre de résultats Amazon est approximatif et varie selon le marché et la requête. Le BSR est relatif et fluctue ; il n'indique pas les ventes quotidiennes exactes. Les avis ne prouvent pas le volume des ventes ni la facilité de se positionner. Il faut compléter l'échantillon par une analyse des sous-catégories, formats, prix, qualité, différenciation et évolution temporelle. Toute donnée absente doit rester absente : pas d'invention ni d'estimation présentée comme observation.

## Utilisation
`PYTHONPATH=runtime python -m papi_core kids-niche-assess chemin/vers/recherche.json`

Le fichier d'entrée doit suivre exactement le schéma validé dans `runtime/papi_core/kids_niche_research.py`. Les tests utilisent des données synthétiques uniquement.
