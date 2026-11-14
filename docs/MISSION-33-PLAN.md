# Mission 33 — Plan de réalisation sur 20 journées

Cette mission est un programme unique de 20 journées, regroupées en quatre phases. Le détail exécutable est dans [le prompt complet](MISSION-33-PROMPT.md).

| Phase | Jours | Résultat attendu |
|---|---:|---|
| A — Contrats et sécurité | 1–5 | Contrats vérifiés, modèle de menace et règles de visibilité |
| B — Planification déterministe | 6–10 | Plans référentiels, empreintes stables, conflits bloquants et tests |
| C — Approbation et reprise | 11–15 | Contrat d'approbation à périmètre fixe, idempotence et runbook de reprise |
| D — Validation opérationnelle | 16–20 | Matrice d'intégration, observabilité, runbook, revue et transfert |

## Exécution réellement réalisée dans cette PR
- Audit documentaire et statique des interfaces Mission 32 et de la feuille de route.
- Ajout d'un planificateur déterministe `build_sync_plan`, sans écriture ni transport de contenu.
- Les entrées identiques sont ignorées ; les divergences restent bloquantes ; les différences produisent seulement des références d'action à faire approuver.
- Ajout d'un digest d'intégrité et de tests adversariaux.
- Les étapes d'approbation cryptographiquement vérifiée, les tests sur projet Supabase réel, les migrations distantes et le déploiement restent des gates ultérieurs non exécutés.

## Règle de clôture
La présence du code ne signifie pas que la synchronisation est opérationnelle. L'activation exige une approbation propriétaire distincte, une frontière serveur vérifiée, un environnement de test autorisé et une revue indépendante.
