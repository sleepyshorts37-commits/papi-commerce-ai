# Mission 44 — Plan de travail sur cinq jours

1. Jour 1 — Auditer les interfaces du spool, du vérificateur Ed25519 et du reçu atomique; définir le contrat d'entrée/sortie.
2. Jour 2 — Implémenter la façade de réception locale avec normalisation des erreurs et conservation du fichier source.
3. Jour 3 — Ajouter la commande CLI avec destination et chemins explicitement fournis par l'opérateur.
4. Jour 4 — Tester le cycle complet, signature invalide, propriétaire inconnu, rejeu, mauvaise destination, paquet altéré, expiration et idempotence.
5. Jour 5 — Documenter l'exploitation, actualiser README/roadmap, vérifier la suite et la CI sur le SHA final; ouvrir une PR brouillon.

Résultat attendu : réception authentifiée et reçu atomique mono-instance; aucun import de contenu, réseau ou exécution.
