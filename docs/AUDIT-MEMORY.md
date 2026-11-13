# Journal d'audit et mémoire opérationnelle

## Module
`runtime/papi_core/audit.py` fournit un journal JSON Lines append-only local.

## Événements
Chaque événement contient un identifiant unique, une date ISO 8601, un acteur, une action, un type et identifiant d'entité, ainsi que des détails structurés limités.

## Utilisation Python
```python
from pathlib import Path
from papi_core.audit import new_event, append_event, read_events

event = new_event(
    event_id="EVT-EXAMPLE-001",
    actor="astou",
    action="task.reviewed",
    entity_type="task",
    entity_id="PAPI-EXAMPLE-001",
    details={"decision": "needs_review"},
)
append_event(event, Path("data/events.jsonl"))
history = read_events(Path("data/events.jsonl"))
```

## Protections
- Refus des clés pouvant contenir secrets, identifiants d'accès, données de carte, coordonnées ou données client.
- Refus des événements incomplets, champs inconnus, formats invalides et journaux corrompus.
- Déduplication par `event_id` pour les appels séquentiels.
- Permissions de création du fichier restreintes au propriétaire du processus lorsque le système les prend en charge.
- Le journal est append-only par convention logicielle : ce module n'offre aucune fonction de modification ou suppression.

## Limites importantes
- Le module est local et n'est pas encore connecté à GitHub Issues, à une base distante ou à un runtime d'agents.
- La déduplication est conçue pour un seul processus écrivain. Un stockage multi-processus ou multi-instance nécessitera une base transactionnelle et des contraintes d'unicité.
- Ne jamais verser de données privées ou de journaux bruts dans le dépôt GitHub public.
- Les événements d'exemple et tests utilisent des données fictives.

## Statut
Brique logicielle créée ; aucune mémoire persistante d'agents n'est déployée ni alimentée automatiquement.


## Contrat de publication externe — prototype

`runtime/papi_core/audit_anchor.py` définit une interface de backend pour publier uniquement un checkpoint (`schema_version`, `sequence`, `head_hash`) dans un service témoin séparément contrôlé.

- Le backend doit fournir une lecture du dernier checkpoint et un `compare_and_append` atomique (compare-and-swap) ; il doit refuser toute modification concurrente, régression de séquence ou remplacement d'un checkpoint existant.
- Avant d'avancer, le code vérifie que le checkpoint précédemment publié correspond bien à un préfixe du journal local. Une simple séquence croissante ne suffit pas à empêcher une bifurcation.
- Une publication identique est idempotente. Une vérification indique le nombre d'événements locaux non encore ancrés ; elle détecte également un journal local tronqué ou réécrit.
- Seuls le numéro de séquence et le hash de tête sont transmis ; aucun événement, contenu métier, identifiant client ou secret n'est envoyé par cette interface.

**Limite de livraison :** aucun backend externe concret, compte fournisseur, stockage indépendant, clé de signature distante ou appel réseau n'est configuré. Les tests utilisent un backend simulé en mémoire. Ce prototype définit et teste le contrat d'intégration ; il ne constitue pas encore un ancrage externe opérationnel ni une preuve de résistance à un administrateur contrôlant le stockage local et le service distant.
