# Mission 197 — Durabilité des archives locales d'audit

## Date et objectif
24 novembre 2026. Compléter le prototype d'archives vérifiables en rendant explicite et testable la synchronisation des entrées de répertoire après création et restauration.

## Constat
Les octets des fichiers étaient synchronisés avant fermeture, mais la durabilité des entrées de répertoire n'était pas garantie explicitement. La création synchronisait le répertoire de l'archive sans synchroniser son parent ; la restauration ne synchronisait pas le répertoire parent après la création du journal et de son fichier de verrouillage.

## Modifications
- Ajoute la fonction _fsync_directory, qui ouvre le répertoire avec O_DIRECTORY et O_NOFOLLOW, vérifie le type via fstat, puis appelle fsync.
- Après création d'une archive, synchronise le répertoire d'archive puis son parent.
- Après restauration et relecture, synchronise le répertoire parent contenant le journal et le verrou.
- Si la synchronisation échoue pendant une restauration, l'opération échoue fermé et tente de supprimer le journal nouvellement créé.
- Ajoute trois tests : ordre des synchronisations lors de la création, synchronisation lors de la restauration, et échec fermé si la synchronisation du parent échoue.
- Met à jour la documentation d'exploitation et la roadmap.

## Limites
- fsync améliore la durabilité locale, mais ne prouve pas la réplication, la sauvegarde hors site, la rétention WORM ou la persistance matérielle du stockage.
- Les opérations restent locales et testées avec un adaptateur d'ancrage mémoire.
- Les tests locaux ne sont pas exécutés dans cette session ; la validation CI sera rapportée après les workflows.
- Aucun fournisseur distant, service, agent, worker ou scheduler n'est activé.

## Gouvernance
Branche dédiée empilée sur Mission 196 (#373). Aucun changement sur main, aucune fusion, aucun déploiement, aucune migration de production, aucun secret, paiement, contact externe ou engagement commercial.
