# Mission 33 — Jours 11 à 15 : approbation et reprise gouvernées

11. Définir une approbation future liée au digest du plan, à la destination et aux actions exactes.
12. L'approbation doit être émise par une identité propriétaire authentifiée dans le backend ; un agent ne peut pas l'émettre pour lui-même.
13. Les clés d'idempotence futures dérivent de l'identifiant d'action immuable ; un retry ne crée pas une deuxième opération.
14. États cibles documentés : proposed, approved, applying, completed, partial, blocked, expired.
15. Runbook de reprise : résultat réseau inconnu, crash, lease expiré, conflit et vérification manuelle.

**État :** contrats et contraintes documentés. Aucun nouvel endpoint d'approbation ni exécuteur de transfert n'est activé dans cette PR ; ce choix évite de présenter une approbation non vérifiée comme autorisation effective.
