# Mission 200 — Inspection sûre des archives interrompues

## Date et objectif

26 novembre 2026. Fournir un inventaire local des archives incomplètes et des fichiers temporaires laissés par une interruption, sans effectuer de récupération destructive ou ambiguë.

## État de départ vérifié

- Mission 199 : PR #376, brouillon ouvert, non fusionnée.
- Branche de base : mission-199-audit-archive-close-before-publish.
- Tête de base : cbd85a2c65a25983a363cc27d45c24c973a7be54.
- Les trois workflows CI de la tête de base ont réussi : 250 tests Python, validation des registres et documentation.
- Aucun avis de revue ou fil de revue ouvert sur la PR #376.
- La chaîne d'archives reste locale ; aucun adaptateur distant n'est configuré.

## Changements

- Ajoute inspect_archive_recovery à runtime/papi_core/audit_archive.py.
- Distingue un dossier structurellement complet mais non vérifié cryptographiquement d'un dossier incomplet.
- Repère les temporaires correspondant aux motifs utilisés par la création d'archive et la restauration.
- Inspecte les métadonnées sans suivre les liens symboliques.
- Signale les permissions trop ouvertes, propriétaire inattendu, types non réguliers, tailles excessives et limites d'inventaire.
- Ajoute la commande locale audit-archive-inspect avec les modes archive-directory et restore-target.
- Ajoute cinq tests : archive structurellement complète, temporaire orphelin dans une archive, temporaire de restauration, lien symbolique et permissions trop ouvertes.
- Met à jour README, documentation d'archives et roadmap.

## Comportement de sécurité

L'inspection est strictement en lecture seule. Elle ne lit pas le contenu des temporaires, ne les renomme pas, ne les promeut pas et ne les supprime pas. Un fichier temporaire n'a pas de preuve autonome liant ses octets à un manifeste et à un checkpoint vérifiés ; il ne peut donc pas être restauré automatiquement.

Le statut structurally_complete_unverified ne remplace pas verify_archive. La vérification cryptographique complète exige toujours un AnchorClient autorisé.

## Validation

- Tests locaux : non exécutés dans cette session.
- Les workflows GitHub Actions de la nouvelle tête doivent confirmer les cinq régressions et les contrôles existants.
- Aucun test sur stockage distant, système WORM, sauvegarde hors site ou panne matérielle n'est revendiqué.

## Limites et prochaine étape

- Les temporaires identifiés nécessitent une revue humaine ; aucun nettoyage automatique n'est proposé.
- L'inspection est limitée à 4096 entrées par répertoire.
- La récupération ne doit être tentée qu'à partir d'une archive cryptographiquement vérifiée ou d'une source d'audit encore valide.
- Étape suivante : définir un protocole de conservation et de quarantaine manuelle, puis un test de restauration après crash sur un système de fichiers de test.

## Gouvernance

PR brouillon empilée sur #376. Aucun changement de main, aucune fusion, aucun déploiement, aucun agent/worker/scheduler activé, aucun compte externe, secret, paiement ou transfert réseau.
