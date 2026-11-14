# Mission 64 — Jour 4 : tests de résilience

Ajout de tests ciblant les interruptions de processus :
- arrêt après remplacement de la clé privée et avant publication du registre ;
- arrêt après publication du registre et avant nettoyage du journal ;
- état ambigu après altération du registre ;
- reprise automatique avant une signature.

Les tests vérifient la cohérence des deux fichiers, la conservation du journal en cas d'ambiguïté et la possibilité de signer uniquement après récupération sûre. Les résultats CI restent la preuve d'exécution finale.
