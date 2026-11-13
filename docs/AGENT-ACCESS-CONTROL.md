# Identité et contrôle d'accès local des agents

## Fonctionnement livré
- Chaque demande de contrôle référence un identifiant d'agent du registre.
- Le statut doit être exactement `active` ; `defined` et `planned` sont refusés.
- La capacité demandée doit figurer dans `permissions`.
- Une interdiction explicite prévaut toujours sur une permission.
- Les statuts `suspended` et `revoked` sont refusés ; une permission retirée du registre est refusée dès le contrôle suivant.
- La préparation d'une carte d'identité ou d'un dossier d'intégration ne crée pas de compte actif et ne modifie pas le registre en place.
- Les changements de permissions doivent être effectués par un processus de confiance ; l'API d'autorisation ne permet pas à un agent de modifier son propre registre.
- Les actions financières, juridiques et externes restent bloquées par la politique globale.
- Les actions réservées au propriétaire ne peuvent jamais être accordées à un agent.

## Limite de sécurité importante
Ce module est un **contrôle d'autorisation local**, pas une authentification d'identité. L'identifiant transmis par un processus n'est pas une preuve cryptographique de son identité. Aucun mot de passe, token ou secret partagé n'est créé ou stocké. Avant le déploiement multi-instance, ajouter une identité de service vérifiable (par exemple jetons courts signés ou identité de workload), une rotation, une révocation et des journaux d'audit. Les clés devront rester dans un gestionnaire de secrets, jamais dans le dépôt.

## Rotation des clés Ed25519

- La rotation écrit une nouvelle clé privée dans un fichier versionné et unique (<agent>.v<version>.<suffixe>.ed25519.pem) ; elle ne remplace plus le fichier de clé précédent.
- Le registre public n'est basculé vers la nouvelle version qu'après l'écriture durable du fichier candidat. La fonction retourne le chemin de la nouvelle clé.
- En cas d'échec de mise à jour du registre, l'ancienne clé et la version publique active restent la référence. Un fichier candidat peut subsister si l'échec survient après le remplacement atomique du registre ; ne jamais le supprimer sans comparer la version et la clé publique actives.
- Après une rotation réussie, les signatures de l'ancienne version sont refusées. Conserver les anciennes clés hors ligne selon la politique de conservation ; ne pas les réutiliser pour signer.
- La révocation change le statut public en revoked et ferme l'authentification. La révocation ne détruit pas les fichiers privés : leur archivage ou destruction relève d'une procédure séparée et contrôlée.

## Délégation et journalisation de gouvernance

- Il n'existe actuellement aucune API de délégation, d'élévation ou de modification de permissions par un agent. Une permission de gestion interne n'autorise pas implicitement à modifier le registre.
- Les changements de statut, de rôle, de responsable ou de permissions doivent être opérés par un processus de confiance, avec revue indépendante ; aucun agent ne peut s'accorder une permission ni en accorder à un autre.
- Le journal local runtime/papi_core/audit.py sait valider et append des événements, mais il n'est pas encore raccordé à un gestionnaire central de mutations du registre. Par conséquent, l'audit automatique et transactionnel des changements de gouvernance n'est pas livré dans cette version.
- Avant d'autoriser une gouvernance multi-agent, implémenter une commande administrative contrôlée qui journalise l'acteur, la cible, les champs modifiés, les anciennes/nouvelles valeurs non sensibles et le résultat ; protéger le registre contre les écritures concurrentes ; faire échouer la mutation si le journal obligatoire ne peut pas être écrit.
- Toute délégation future devra être bornée par le périmètre du délégant, expirer, être révocable, interdire les permissions propriétaires/sensibles et produire un événement d'audit. Ces règles ne sont pas présentées comme déjà opérationnelles.

## Test
`PYTHONPATH=runtime python -m unittest discover -s tests -p 'test_authz.py' -v`

## État
Aucun agent du registre n'est activé par ce changement. Aucun accès externe n'est ouvert et aucune action n'est exécutée.
