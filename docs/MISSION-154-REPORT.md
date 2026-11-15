# Mission 154 — Politique de rétention et santé des sauvegardes

## Livrable
- Planificateur non destructif : 7 sauvegardes quotidiennes, 4 hebdomadaires et 12 mensuelles par défaut.
- Distingue les sauvegardes à conserver et les candidates à suppression ; aucune suppression n'est exécutée.
- Exige nom unique, SHA-256 et date UTC timezone-aware ; refuse les dates futures.
- Évaluation de santé : dernière sauvegarde de moins de 24 h, copie hors site vérifiée avec preuve, test de restauration réussi depuis moins de 30 jours.
- Rapport de blocages exploitable par l'équipe opérations.
- Tests de rétention, intégrité, fraîcheur et preuves hors site.

## Limites
La synchronisation distante, la planification périodique et la suppression effective ne sont pas activées. Toute suppression exigera une approbation humaine explicite et une conservation hors site vérifiée.
