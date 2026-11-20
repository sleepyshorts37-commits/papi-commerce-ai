# Mission 188 — Limiter les permissions des profils au registre central

## Objectif
Empêcher le registre documentaire des profils professionnels d'élargir les permissions déclarées ou de contourner les interdictions du registre central des agents.

## Changements
- `validate_agent_profiles` exige et valide les listes centrales `permissions` et `prohibited`.
- Les permissions de profil doivent être un sous-ensemble de `agents[id].permissions`.
- Toute permission de profil figurant dans `agents[id].prohibited` provoque une erreur.
- Les permissions déléguables restent un sous-ensemble des permissions propres au profil.
- Tests de régression : permission non déclarée au registre central, permission interdite et délégation non déclarée dans le profil.
- Mise à jour de `docs/AGENT-IDENTITY.md` et de la roadmap.

## État
- Implémenté sur une branche empilée au-dessus de la PR #364.
- PR #365 brouillon vers la branche de fiabilité #364.
- Aucun agent activé ; le registre `data/agent_profiles.json` reste vide.
- Le profil reste documentaire : ce contrôle ne remplace ni la cryptographie ni l'autorisation runtime.

## Validation
Les résultats CI doivent être confirmés sur le SHA final de cette branche. Aucun test local n'est revendiqué dans cette session.

## Limites et prochaine étape
- Le contrôle runtime n'utilise pas ce registre documentaire comme source d'autorisation.
- Les permissions effectives ne doivent être calculées qu'après validation des registres.
- La prochaine étape recommandée est un contrat de synchronisation versionné et testable entre agent/profile/policy, sans activation ni changement d'accès.
