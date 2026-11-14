# Registre local des reçus de synchronisation — Mission 41

## Finalité
Enregistrer durablement qu'un paquet référentiel précis a passé la validation Ed25519 de Mission 40. Le registre SQLite conserve uniquement le digest, le propriétaire, les instances source/destination, l'export, l'identifiant d'approbation et les références/empreintes des événements.

## Transaction
1. Valider signature, propriétaire, scope, TTL, digest et destination attendue.
2. Consommer le nonce anti-rejeu local selon le mécanisme existant.
3. Ouvrir une transaction SQLite immédiate.
4. Inscrire le reçu et toutes les références, avec contraintes uniques sur digest, événement et ressource (type, identifiant).
5. En cas de conflit ou d'erreur, annuler toute l'écriture du reçu.
6. Un digest déjà enregistré est reconnu idempotemment après une nouvelle approbation valide.

## Garanties
- Aucun corps de message, contenu mémoire, donnée client ou secret n'est enregistré.
- Un événement ou une ressource déjà attribué à un autre paquet provoque un rejet.
- Les écritures du reçu et de ses lignes sont atomiques dans la base locale.
- Aucun import, transport, worker ou changement dans PAPI CHAT/mémoire.
- Répertoire privé 0700 et base SQLite 0600.

## Limites
Le registre et l'anti-rejeu sont locaux à une installation. La consommation du nonce (Mission 40) et l'écriture du reçu sont deux transactions distinctes : une panne entre les deux peut consommer le nonce sans inscrire le reçu. Il n'y a donc pas encore d'atomicité distribuée approbation+import. Aucun transport, import transactionnel, verrouillage multi-instance, réplication ou service Supabase distant n'est activé.

## Reprise opérateur
Si la vérification réussit mais que l'écriture échoue, ne pas réutiliser l'enveloppe signée : produire une nouvelle approbation avec un nonce neuf pour le même paquet, après contrôle humain. Un conflit doit être examiné; ne jamais supprimer ni écraser un reçu pour forcer le passage.
