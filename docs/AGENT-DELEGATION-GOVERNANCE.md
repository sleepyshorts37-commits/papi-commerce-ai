# Gouvernance des agents — délégation et hiérarchie

## Principes

- Une identité suspendue ou révoquée ne peut participer à une délégation.
- Seul le responsable hiérarchique direct peut proposer une délégation.
- Le délégant doit posséder explicitement `delegate_tasks` et chacune des permissions demandées.
- Les permissions demandées doivent aussi appartenir au plafond déclaré du délégataire : la délégation ne peut donc pas élargir ses capacités.
- L'auto-délégation, les responsables inconnus, les cycles hiérarchiques et les permissions dupliquées sont refusés.
- Une proposition autorisée est un reçu de contrôle, pas une modification de rôle ou une activation d'agent.

## Audit et révocation

Chaque décision réelle de délégation devra être enregistrée dans le journal d'audit avec les identifiants des deux agents, les permissions précises, l'acteur, l'horodatage, le résultat et le motif d'un refus. Les secrets et clés privées ne doivent jamais figurer dans cet événement.

La suspension ou révocation d'une identité doit être vérifiée à chaque nouvelle décision. Les systèmes d'exécution devront aussi réévaluer les permissions avant chaque action sensible ; un reçu ancien ne constitue pas une autorisation permanente.

## Limites de cette étape

Le module `agent_governance` valide la hiérarchie et calcule si une délégation est admissible. Il ne persiste aucun droit, ne crée aucun agent, ne provisionne aucune clé, n'active aucun worker et n'exécute aucune action. Les identités actuellement définies dans le registre ne sont pas automatiquement déclarées actives. Le statut `active` est exigé par la politique, mais les agents PAPI restent en mode de conception/préparation tant qu'un processus d'activation distinct et approuvé n'existe pas.

Ce contrôle applicatif doit être complété en production par des permissions vérifiées côté serveur, une source de révocation fortement cohérente et des tests de concurrence/révocation. Il ne remplace pas les contrôles de la plateforme ni l'approbation humaine pour les actions financières, juridiques ou externes.
