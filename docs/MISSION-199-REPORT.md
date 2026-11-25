# Mission 199 — Fermer le temporaire avant publication atomique des archives

## Date et objectif
25 novembre 2026. Éliminer le cas où une erreur de fermeture du descripteur après la création du lien final laisse une cible visible alors que l'appelant reçoit un échec et n'enregistre pas la création.

## Constat reproductible
Dans la version précédente, le lien matériel vers le chemin final était créé avant `os.close(descriptor)`. Si la fermeture échouait, l'appel levait une exception après publication. La restauration pouvait alors laisser un journal final sans fichier de verrouillage, et la création d'archive pouvait laisser un répertoire incomplet que le nettoyage ne pouvait pas retirer.

## Modifications
- Écrit les octets dans un temporaire privé du même répertoire.
- Gère les écritures partielles et `InterruptedError`.
- Synchronise le contenu avec `fsync`, vérifie le type du fichier, puis ferme le descripteur avant publication.
- Ne crée le lien matériel atomique sans écrasement qu'après une fermeture réussie.
- Supprime le temporaire dans un bloc de nettoyage exécuté même si la fermeture échoue.
- Ajoute deux tests de régression : échec de fermeture pendant une restauration et pendant la création d'une archive.
- Met à jour la documentation d'archives et la roadmap.

## Validation
- Base de travail : PR #375, branche `mission-198-atomic-audit-file-publication`, SHA `f109a01fa5557c7bc70d56875f9ecc911dddf144`.
- Tests locaux : non exécutés.
- Les workflows GitHub Actions seront déclenchés par l'ouverture de la PR #376 ; leur résultat et le SHA exact seront consignés dans le rapport de session.
- Aucun test de système de fichiers distant, de stockage WORM ou de panne matérielle n'est revendiqué.

## Limites
- Un échec de suppression du temporaire peut laisser un fichier caché ; la vérification stricte de l'archive refuse les entrées supplémentaires.
- Les liens matériels et `fsync` de répertoire dépendent des capacités du système de fichiers et de la plateforme.
- Aucun adaptateur distant, réplication ou sauvegarde hors site n'est ajouté.

## Gouvernance
PR brouillon empilée sur #375. Aucun changement de `main`, aucune fusion, aucun déploiement, aucun worker/agent activé, aucun secret, service externe ou paiement utilisé.

## Ajustement de validation
La première exécution CI sur le SHA `603675e497943b28f74704615f3d9eac3ccdbf07` a exécuté 250 tests et révélé un défaut dans le test d'injection de panne : le compteur interceptait une fermeture du fichier temporaire de vérification avant d'atteindre le descripteur de restauration. Le test a été corrigé pour cibler explicitement le descripteur créé par le second `mkstemp`. Le code de production n'a pas été modifié à la suite de cet échec. La CI de la nouvelle tête doit confirmer les deux scénarios.

## Résultats CI vérifiés

Après correction du ciblage du descripteur dans les tests, la tête de code `4c544a20800f3acca2c1fac209a95092f0bd63f0` a obtenu :
- [PAPI core tests — run #2867](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45621865603) : succès, **250 tests exécutés, 250 réussis, 0 échec** ; les deux nouveaux tests de fermeture sont `ok`.
- [PAPI registry validation — run #927](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45621865884) : succès.
- [PAPI documentation checks — run #894](https://github.com/sleepyshorts37-commits/papi-commerce-ai/actions/runs/45621865551) : succès.
- `pip check` : aucune dépendance cassée.
- Deux exécutions `pip-audit --strict` : aucune vulnérabilité connue détectée dans les graphes analysés.
- PostgreSQL 16 jetable : schéma de base, compatibilité legacy, migration durable, réservations concurrentes avec `SKIP LOCKED` et rollback réussis.

La première exécution sur `603675e497943b28f74704615f3d9eac3ccdbf07` a échoué sur un seul test de régression parce que le mock interceptait une fermeture antérieure pendant la vérification. Le test a été corrigé pour identifier le descripteur du second `mkstemp`. Aucun défaut de production n'a été révélé par cet échec initial. La tête de code corrigée a passé les 250 tests.
