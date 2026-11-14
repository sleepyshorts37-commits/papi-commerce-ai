# Validation du Jour 2 — Mission 17

La suite CI standard du dépôt doit s'exécuter sur le commit de tête de la PR.

Contrôles attendus :
- Core Tests : import des adaptateurs et exécution des tests RSS/JSON.
- Registry Validation : JSON du registre conforme.
- Documentation Checks : présence des documents requis.

Le contrôle Supabase Preview peut être ignoré lorsque les previews sont désactivées au niveau du projet ; ce statut n'est pas une validation des tests applicatifs.

Ne pas considérer les parseurs comme des connecteurs réseau actifs. Ils consomment uniquement des payloads remis par une source autorisée et ne déclenchent aucune action externe.
