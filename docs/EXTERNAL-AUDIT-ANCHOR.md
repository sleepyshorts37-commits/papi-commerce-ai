# Prototype d'ancrage externe du journal d'audit

## Objectif et état

runtime/papi_core/anchor.py définit un contrat fournisseur-neutre pour publier des checkpoints SHA-256 du journal d'audit. Aucun fournisseur, compte, endpoint, jeton ou abonnement n'est configuré. Aucun appel réseau n'est effectué par ce module.

L'adaptateur externe devra fournir :
- get_head() pour lire le pointeur de tête ;
- get_checkpoint(id) pour relire les octets d'un checkpoint ;
- put_checkpoint(id, payload) pour une écriture immuable et idempotente ;
- compare_and_swap_head(expected, replacement) pour empêcher deux écrivains de faire avancer la même tête.

Le prototype exige un stockage qui refuse la réécriture d'un identifiant avec un contenu différent. La mise à jour de tête doit être atomique côté fournisseur.

## Format et vérification

Chaque checkpoint contient la version, un identifiant, le numéro de séquence du journal, le hash SHA-256 de la tête du journal local, l'identifiant du checkpoint précédent et la date UTC. Le digest est calculé sur un JSON canonique (clés triées, séparateurs stables). La vérification recalcule le digest et parcourt tous les parents jusqu'à la racine.

Un hash détecte une altération par rapport à un checkpoint de confiance ; il ne prouve pas à lui seul l'identité de l'auteur. Une protection contre un administrateur qui contrôle simultanément le stockage et son pointeur exige une séparation des domaines de confiance, une rétention immuable/WORM ou une signature conservée dans un domaine indépendant.

## Reprise et rollback

Après une erreur réseau ambiguë, l'appelant doit réutiliser le même checkpoint_id. Le client relit le checkpoint, vérifie son contenu et réconcilie le pointeur de tête. Une nouvelle tentative avec un autre identifiant pourrait créer un doublon logique.

Le rollback déplace le pointeur vers un ancêtre vérifié par compare-and-swap. Il ne supprime pas les checkpoints plus récents : ils restent disponibles comme éléments de preuve. Une nouvelle branche peut ensuite repartir de l'ancêtre restauré.

Les suppressions ou altérations d'un checkpoint référencé sont détectées à la lecture. Le stockage externe réel doit conserver les objets et les têtes avec des droits séparés ; le protocole seul ne peut pas empêcher un fournisseur ou un administrateur privilégié de supprimer toute la chaîne.

## Tests et limites

tests/test_anchor.py utilise un adaptateur mémoire exclusivement en test. Il couvre publication, hash, altération, suppression, rollback, concurrence, collision d'identifiant, erreur réseau et reprise après perte de réponse.

Ce test ne valide ni une API distante, ni la durabilité multi-région, ni une rétention WORM. Aucun ancrage n'est considéré actif tant qu'un adaptateur externe gratuit, autorisé, testé et doté d'une procédure de récupération n'a pas été choisi et revu.
