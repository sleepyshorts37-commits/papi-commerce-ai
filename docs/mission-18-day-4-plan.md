# Mission 18 — Jour 4/5 : classement transparent des opportunités

## Objectif
Prioriser les pistes pour revue humaine selon la fraîcheur, la complétude, l'admissibilité déclarée, les données économiques, le statut de la source et la cohérence des preuves.

## Réalisations
- Ajout d'un classement déterministe et explicable, sans score probabiliste.
- Blocage des pays explicitement non admissibles, des revenus nets non positifs, des dates futures et des preuves contradictoires.
- Absence de bonus en cas de données économiques inconnues ; les sources non vérifiées ne peuvent pas atteindre la priorité de revue.
- Tri stable et conservation des motifs et blocages.
- Tests couvrant les cas favorables, inconnus, contradictoires, non admissibles et négatifs.

## Sécurité
Le classement ne qualifie jamais une candidature et ne déclenche aucune action externe. Aucune navigation, inscription, candidature, dépense ou transaction.
