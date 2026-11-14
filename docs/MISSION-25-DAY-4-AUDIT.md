# Mission 25 — Jour 4 : audit et intégration contrôlée

## Événements d'audit recommandés
Conserver uniquement : identifiant d'événement, identifiant d'approbation, identifiant de tâche, handler, classe d'action, décision, identifiant du propriétaire, horodatage UTC et résultat du contrôle.

## Données interdites dans l'audit
Ne jamais journaliser payload, corps de message, données client, secret, jeton de session, OTP, PIN, CVV ou contenu de pièce justificative.

## Séquence d'intégration future
1. Authentifier le propriétaire via une interface sécurisée.
2. Construire l'attestation côté serveur, jamais depuis un payload agent.
3. Valider la portée et la fenêtre de validité.
4. Consommer l'identifiant via une opération atomique à contrainte unique.
5. Enregistrer l'événement d'audit minimal.
6. Revalider la politique globale avant toute exécution autorisée.
7. En cas d'incertitude, refuser et demander une nouvelle approbation.

## Résultat
Procédure documentée. Aucun stockage persistant, interface propriétaire ou handler externe n'est activé.
