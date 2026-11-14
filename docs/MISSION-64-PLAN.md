# Mission 64 — Ed25519 crash-consistent key rotation

## Objectif
Éliminer le risque de désynchronisation entre le fichier de clé privée et le registre public lors d'une rotation Ed25519 interrompue par un arrêt brutal du processus. La mission complète la conservation historique de Mission 63 ; elle ne réactive jamais une ancienne clé pour l'authentification courante.

## Prompt détaillé d'exécution

Agir comme ingénieur senior en cryptographie appliquée, stockage local durable, systèmes de fichiers POSIX et sécurité Python. Examiner les implémentations réelles avant modification, préserver les API existantes et démontrer chaque transition par des tests de panne simulée. Ne jamais publier de clé privée, journal réel, secret ou donnée utilisateur.

### Jour 1 — Audit et conception
1. Examiner `identity_ed25519.py`, le registre public versionné, la rotation, la signature, la révocation et les tests historiques.
2. Décrire les fenêtres de panne : avant journal, après journal, après remplacement de la clé privée, après publication du registre et avant suppression du journal.
3. Définir une transaction locale à deux fichiers avec un journal durable, des SHA-256 des états ancien/nouveau et des copies de récupération strictement protégées.
4. Définir les états récupérables : non démarré, rollback requis, commit achevé ; tout état ambigu doit échouer fermé et préserver les preuves.
5. Documenter les limites : fsync dépend du système de fichiers et du système d'exploitation ; pas de garantie sur stockage défaillant ou contrôleur qui ment.

### Jour 2 — Journal transactionnel
1. Créer un module dédié au journal de rotation.
2. Créer le journal de façon exclusive, mode 0600, avec fsync du fichier et du répertoire.
3. Inclure uniquement les octets nécessaires aux états ancien/nouveau, leurs empreintes SHA-256, l'identifiant de transaction et le nom de la clé concernée.
4. Valider le type de fichier, le propriétaire, les liens et les permissions avant lecture.
5. Ne jamais afficher, journaliser ou copier les clés privées hors du répertoire protégé.

### Jour 3 — Intégration et récupération
1. Remplacer la rotation multi-écriture non protégée par : journal durable, remplacement atomique de la clé privée, remplacement atomique du registre public, suppression durable du journal.
2. Récupérer avant toute nouvelle rotation et avant toute signature locale.
3. Si le registre est ancien et la clé privée nouvelle, restaurer l'ancienne clé.
4. Si le registre et la clé privée sont tous deux nouveaux, confirmer le commit et supprimer le journal.
5. Si les empreintes ne correspondent à aucun état attendu, refuser la signature/rotation et conserver le journal pour intervention manuelle.
6. Préserver l'historique de clés de Mission 63 et les signatures historiques.

### Jour 4 — Tests de résilience
1. Simuler un arrêt brutal après création du journal.
2. Simuler un arrêt après remplacement de la clé privée et avant publication du registre.
3. Simuler un arrêt après publication du registre et avant suppression du journal.
4. Simuler un journal altéré, des empreintes incorrectes, un lien symbolique et des permissions trop ouvertes.
5. Vérifier que l'état ambigu n'est jamais deviné ou effacé.
6. Vérifier qu'une signature après reprise utilise la clé et la version cohérentes.

### Jour 5 — Validation et clôture
1. Exécuter les tests ciblés Ed25519 et la suite Python complète.
2. Vérifier le workflow CI sur le SHA final exact.
3. Mettre à jour le runbook, la roadmap et les limites opérationnelles.
4. Vérifier qu'aucune clé privée ou donnée réelle n'a été ajoutée au dépôt.
5. Ouvrir une PR brouillon basée sur Mission 63, sans fusion ni déploiement.

## Critères d'acceptation
- Journal transactionnel exclusif et durable.
- Récupération déterministe des états ancien/ancien, nouveau/ancien et nouveau/nouveau.
- État ambigu : fail-closed, journal conservé.
- Récupération automatique avant signature et nouvelle rotation.
- Historique des clés et vérification d'archives préservés.
- Tests de panne et CI verts sur le SHA exact.
- Aucun agent, worker, scheduler ou service externe activé.

## Gouvernance
Aucune connexion réseau, migration distante, déploiement, publication, dépense, paiement, communication externe ou activation d'agent. Les anciennes clés restent réservées à la preuve historique et n'accordent aucune autorisation.
