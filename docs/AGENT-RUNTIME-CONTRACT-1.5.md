# PAPI AGENT RUNTIME CONTRACT 1.5

## Objet

Le module `papi_core.execution_gate` définit un précontrôle déterministe avant toute future exécution de tâche par un agent. Il retourne une décision explicable et des codes de blocage. Il ne démarre pas de worker et n'appelle aucun handler.

## Contrôles

- Activation globale explicite via `execution_enabled: true` (la configuration du projet reste à `false`).
- Tâche au statut `ready`, identifiant présent et propriétaire correspondant à l'agent.
- Agent actif et carte d'identité active, complète, structurellement valide.
- Concordance exacte des permissions et interdictions entre registre et carte.
- Approbation propriétaire si la tâche ou la permission l'exige.
- Spécification `execution` contenant handler, permission, catégorie et coût.
- Handler dans `allowed_handlers`; permission accordée et non interdite.
- Catégorie autorisée par `action_permissions`; contrôle du budget en FCFA.
- Les catégories financières et juridiques sont toujours bloquées par ce précontrôle. Les communications externes restent désactivées selon la politique actuelle.

## Format minimal d'une tâche candidate

```json
{
  "id": "TASK-EXAMPLE",
  "owner_agent": "agent-a",
  "status": "ready",
  "approval_required": false,
  "execution": {
    "handler": "internal.echo",
    "permission": "read_reports",
    "category": "read_only",
    "cost_xof": 0
  }
}
```

## Garanties et limites

- `eligible` signifie uniquement que les contrôles de prévalidation ont réussi.
- `execution_performed` et `execution_token_issued` restent toujours à `false`.
- Aucun processus, commande, API, message, achat, transfert ou écriture n'est déclenché.
- Le résultat n'est ni une authentification cryptographique, ni une autorisation durable, ni un jeton utilisable par un worker. L'authentification Ed25519 doit rester effectuée par le chemin d'authentification dédié au moment de toute future demande.
- Le budget du projet reste à 0 FCFA et `execution_enabled` reste à `false`.
- Les profils des 40 agents restent planifiés/incomplets ; aucun agent n'est activé.

## Vérification

Les tests unitaires couvrent le refus par défaut, l'identité inactive/incomplète, les permissions, l'approbation, l'état de tâche, les actions externes et le budget nul. Les tests automatisés et la connexion réelle à Supabase doivent être vérifiés séparément.
