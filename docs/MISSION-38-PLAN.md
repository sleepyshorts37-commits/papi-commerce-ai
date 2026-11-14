# Mission 38 — Plan de travail

| Jour | Lot | Livrable |
|---|---|---|
| 1 | Audit PAPI CHAT, mémoire et sync existante | Matrice capacités / limites |
| 2 | Contrat paquet versionné | Format canonique et règles d'intégrité |
| 3 | Idempotence, conflit et anti-rejeu | Politique fail-closed |
| 4 | Scénarios et tests locaux synthétiques | Matrice de tests négatifs/positifs |
| 5 | Documentation, CI et livraison | Rapport, PR draft et SHA vérifié |

## Conditions de sortie
Le protocole doit être compris et auditable; les scénarios de rejeu, altération, divergence et reprise doivent avoir une réponse déterministe. Aucune connexion ou opération externe n'est requise.

## Hors périmètre
Synchronisation distante réelle, modification du schéma Supabase distant, déploiement, activation de workers/schedulers, transfert de messages ou mémoire de l'utilisateur, et toute opération commerciale/financière.