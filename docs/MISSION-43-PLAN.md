# Mission 43 — Plan de travail sur cinq jours

| Jour | Travail | Résultat attendu |
|---|---|---|
| 1 | Audit du paquet canonique, de l'approbation et des menaces du transfert manuel | Contrat et menaces documentés |
| 2 | Format JSON versionné, taille maximale, empreinte de paquet | Enveloppe déterministe |
| 3 | Spool local, permissions 0700/0600, écriture temporaire et création atomique sans écrasement | Fichier durable et privé |
| 4 | Lecture défensive, rejet des liens symboliques, doublons JSON et altérations | Tests de régression |
| 5 | Documentation opérateur, validation CI et rapport final | PR brouillon prête à revue |

## Critères d'acceptation
- Un paquet est limité à 2 Mio et nommé par son SHA-256.
- L'écriture n'écrase jamais un fichier existant.
- La lecture vérifie l'intégrité, la structure et la correspondance approbation/paquet.
- Les permissions locales sont restrictives.
- Lire un paquet ne vérifie pas la signature, ne consomme pas le nonce et n'importe rien.
- Aucun réseau, worker, scheduler, déploiement ou action externe.
