# Mission 203 — Restauration d'archives attachée au descripteur de destination

Date : 2026-11-27

## Objectif

Éliminer la re-résolution path-based dans la publication d'un journal restauré. La vérification de l'archive était déjà attachée à des descripteurs épinglés (Mission 202), mais la destination de restauration repassait par les chemins absolus après un contrôle préalable des parents.

## Changements

- Ouvre chaque composant du parent cible avec la chaîne _open_directory_chain.
- Exige que le parent final appartienne au processus courant et ne soit pas modifiable par le groupe ou les autres.
- Ouvre et verrouille le sidecar .lock relativement au parent épinglé ; valide le type régulier, le propriétaire, le mode privé et l'absence de contenu.
- Crée le temporaire relativement au descripteur, l'écrit complètement, le synchronise et le ferme avant de publier par lien matériel atomique sans écrasement.
- Relit les octets depuis le même descripteur de parent et valide à nouveau la chaîne JSONL sans re-résoudre le chemin cible.
- Effectue le fsync et le rollback relativement au même parent épinglé.
- Conserve le sidecar de verrouillage après un échec post-création : le supprimer pourrait laisser un autre processus verrouiller un inode désormais détaché et permettre une course avec un nouveau sidecar.
- Ajoute un test de régression qui remplace un ancêtre par un lien symbolique juste avant l'ouverture du composant enfant ; la restauration doit rester attachée au répertoire initial.
- Met à jour la documentation et la roadmap.

## Validation

La validation locale n'est pas exécutée dans cet environnement. Les tests et contrôles CI seront vérifiés après ouverture de la PR et sur le SHA exact.

## Limites

- Les ancêtres et le système de fichiers doivent rester des emplacements de confiance ; un processus de même UID qui contrôle le répertoire déjà ouvert reste hors du modèle de menace.
- Le parent final doit appartenir au processus courant et ne pas être modifiable par le groupe ou les autres.
- Le lien matériel, dir_fd, O_NOFOLLOW, O_DIRECTORY et flock doivent être disponibles ; sinon, l'opération échoue fermé.
- La création d'archive reste path-based et constitue un incrément distinct à traiter.
- Aucun test de panne matérielle, de stockage distant ou de réplication n'est revendiqué.

## Gouvernance

Branche dédiée empilée sur Mission 202 (#379). Aucun changement de main, aucune fusion, aucun déploiement, aucun worker/agent réel activé, aucune base de production, aucun secret ni aucune action financière ou commerciale externe.
