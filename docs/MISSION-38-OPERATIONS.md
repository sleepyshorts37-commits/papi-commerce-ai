# Mission 38 — Notes opérateur : synchronisation contrôlée

## État
Cette mission définit les exigences de préparation. Elle n'active aucun transport et ne constitue pas une procédure autorisant la synchronisation réelle.

## Principes obligatoires
1. Conserver les journaux originaux en lecture seule avant toute analyse ou import.
2. Vérifier la version de protocole, l'identité de l'instance source et la destination autorisée.
3. Calculer le digest du paquet sur une représentation canonique définie par le protocole.
4. Vérifier la signature et l'approbation explicite liée au digest, à la destination, à la portée et aux IDs ordonnés.
5. Prévalider toutes les entrées; en cas d'écart, rejeter le paquet entier sans écriture partielle.
6. Dédupliquer uniquement si ID et digest du contenu concordent. ID identique et contenu différent = conflit à examiner.
7. Ne jamais écraser ni supprimer une entrée append-only; placer les conflits en quarantaine traçable.
8. Garder les clés privées et données sensibles hors du dépôt et des journaux de diagnostic.
9. Sauvegarde et restauration doivent être testées sur des données synthétiques isolées.

## Interruption / arrêt
En l'absence de transport et d'importateur activés, aucun arrêt de service n'est nécessaire. Si un futur déploiement est autorisé, suspendre l'import, préserver les journaux, révoquer les credentials compromis et demander une revue propriétaire avant reprise.

## Limites
Le contrat documentaire ne garantit pas la cohérence distribuée, l'authenticité de serveurs distants, la protection contre les pannes réseau ou l'exécution atomique tant qu'un adaptateur et ses tests d'intégration ne sont pas implémentés et approuvés.