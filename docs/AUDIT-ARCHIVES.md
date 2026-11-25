# Archives vérifiables du journal d'audit

## Objectif et périmètre

`runtime/papi_core/audit_archive.py` fournit un format local de snapshot complet du journal JSONL. Il ne réalise ni rotation, ni purge, ni découpage du journal source. L'archive est une copie autonome du journal entier au moment de l'ancrage.

La création exige :
- un journal source lisible et vérifié par `read_events` ;
- un checkpoint déjà publié et dont toute la chaîne d'ancêtres est vérifiable ;
- un checkpoint courant dont le numéro de séquence et le hash de tête correspondent exactement au journal copié ;
- un nouveau répertoire de destination, qui ne doit pas déjà exister.

Aucun adaptateur d'ancrage de production n'est configuré. Le seul adaptateur concret du dépôt reste le stockage mémoire des tests. Cette API n'est donc pas un service d'archivage opérationnel.

## Format d'archive

Le répertoire contient exactement deux fichiers :
- `journal.jsonl` : copie exacte des octets du journal ;
- `manifest.json` : JSON canonique contenant version, identifiant d'archive, date UTC, SHA-256 et taille du journal, nombre d'événements, hashes du premier et du dernier événement, identifiant/digest/séquence du checkpoint.

Le manifeste ne contient ni chemin source, ni contenu d'événement, ni donnée client supplémentaire. Les fichiers sont créés en mode privé 0600 et le répertoire en 0700. Les liens symboliques, fichiers non réguliers, propriétaires inattendus, permissions trop ouvertes, fichiers trop volumineux, clés JSON dupliquées et encodages non canoniques sont refusés.

## API locale

L'appelant fournit un `AnchorClient` déjà configuré avec un adaptateur autorisé :

```python
from pathlib import Path
from papi_core.audit_archive import (
    create_verified_archive,
    verify_archive,
    restore_verified_archive,
)

summary = create_verified_archive(
    Path("data/events.jsonl"),
    Path("private-archives/audit-2026-11-24"),
    anchor_client,
)
verified = verify_archive(
    Path("private-archives/audit-2026-11-24"),
    anchor_client,
)
restored = restore_verified_archive(
    Path("private-archives/audit-2026-11-24"),
    Path("recovery/events.jsonl"),
    anchor_client,
)
```

- `create_verified_archive` vérifie la source, relit et valide la copie exacte, puis lie le manifeste au checkpoint courant.
- `verify_archive` recalcule l'empreinte, vérifie le JSONL complet et retrouve le checkpoint dans la chaîne d'ancrage vérifiée. Une archive ancienne reste vérifiable si son checkpoint demeure un ancêtre présent.
- `restore_verified_archive` vérifie d'abord l'archive, puis restaure vers un chemin absent en mode 0600 et relit le journal restauré. Un chemin existant n'est jamais remplacé ni supprimé.

La restauration crée aussi le fichier de verrouillage local attendu par le lecteur du journal. Le journal source n'est jamais modifié.

Les fichiers restaurés sont d'abord écrits dans un fichier temporaire privé du même répertoire, puis synchronisés avant publication par lien matériel atomique sans écrasement. Une interruption pendant l'écriture ne rend donc pas visible un journal final partiel. Le système de fichiers doit prendre en charge les liens matériels ; sinon, la restauration échoue fermé. Un arrêt brutal peut laisser un temporaire caché ; un dossier d'archive contenant un tel résidu ne passe pas la vérification stricte et doit être examiné manuellement.

## Durabilité locale

Chaque fichier est synchronisé (fsync) avant fermeture. Après création, le code synchronise le répertoire de l'archive puis son répertoire parent afin de persister les deux fichiers et l'entrée du dossier d'archive. Après restauration, il synchronise le répertoire parent après la vérification du journal restauré et la création du fichier de verrouillage. Si la plateforme ne permet pas d'ouvrir un répertoire sans suivre un lien symbolique, ou si la synchronisation échoue, l'opération échoue fermé et la cible nouvellement créée est supprimée lorsque possible.

Ces appels améliorent la durabilité locale face à un crash du processus ou du système, mais ne prouvent pas la persistance matérielle du contrôleur/disque, la réplication, la sauvegarde hors site ni la durabilité d'un stockage distant.

## Tests et limites

`tests/test_audit_archive.py` couvre la création, la vérification, le checkpoint périmé, l'absence d'ancrage, la collision de destination, l'altération des octets, les clés dupliquées du manifeste, les liens symboliques, la restauration et la vérification d'une archive après un checkpoint plus récent.

Ces tests utilisent uniquement un adaptateur mémoire en processus. Ils ne prouvent pas la durabilité d'un stockage distant, la rétention WORM, la sauvegarde hors site, la restauration après sinistre ou la protection contre un administrateur qui contrôle à la fois le journal et le stockage d'ancrage.

Aucune suppression du journal source, aucun transfert réseau, aucun chiffrement par clé secrète et aucune rotation automatique ne sont implémentés. Les archives contiennent le journal complet : elles doivent rester dans un stockage privé, chiffré au niveau du système ou du volume selon la politique retenue. Ne jamais les committer dans le dépôt public.

## Statut

Prototype local codé ; tests CI à confirmer sur le SHA de la PR. Aucun fournisseur externe, compte, worker, scheduler ou processus permanent n'est configuré. Une revue indépendante et un adaptateur de stockage autorisé restent requis avant toute utilisation opérationnelle.
