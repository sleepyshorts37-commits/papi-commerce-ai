# Mission 43 — Prompt de réalisation

Sur cinq journées, construire un échange hors ligne sûr pour les paquets de synchronisation PAPI COMMERCE AI, sans modifier les rôles, la hiérarchie ou les responsabilités des agents.

1. Jour 1 — Auditer le contrat des paquets, les signatures Ed25519 et les risques du transport manuel.
2. Jour 2 — Définir un format canonique versionné, borné en taille, sans contenu métier.
3. Jour 3 — Implémenter l'écriture atomique locale, les permissions restrictives et l'interdiction d'écrasement.
4. Jour 4 — Implémenter la lecture défensive et les tests d'altération, liens symboliques, doublons JSON et incohérences.
5. Jour 5 — Documenter la procédure opérateur, les limites de confiance et les critères de validation CI.

Garde-fous : aucune connexion réseau, aucun transfert automatique, aucune consommation de nonce à la simple lecture, aucun import, aucun worker/scheduler activé, aucun déploiement et aucune action externe ou financière.
