# PAPI AI WORKERS — relais humain et reprise du parcours

## Mission 19 — Jour 3/5

Le module `papi_core.human_handoff` formalise le point où un agent doit s'arrêter pour demander une action personnelle à l'utilisateur, puis reprendre après confirmation explicite.

### Cycle d'état
`awaiting_user` → `user_confirmed` → `resumed` → `completed` ou `rejected`.

Aucune reprise n'est possible avant une attestation explicite de l'utilisateur. Cette attestation est enregistrée comme telle et n'est pas présentée comme une vérification technique du compte externe.

### Fonctions
- `create_handoff(...)` : crée une demande avec URL HTTPS officielle et action attendue.
- `confirm_user_action(...)` : enregistre la confirmation utilisateur.
- `resume_after_user_confirmation(...)` : autorise le changement d'état vers la reprise.
- `close_handoff(...)` : clôture le dossier avec un résultat.

### Confidentialité
Les mots de passe, OTP, clés privées, phrases de récupération, données de carte et jetons d'accès sont interdits dans le contexte et la confirmation. L'utilisateur effectue lui-même les étapes confidentielles sur le site officiel.

### Limites
Il s'agit d'un moteur d'état pur avec journal d'événements. La persistance, la livraison de notifications et le raccordement aux connecteurs restent à intégrer. Aucune inscription ni action externe n'est réalisée.
