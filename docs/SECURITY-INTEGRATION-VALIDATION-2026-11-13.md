# Revue d'intégration sécurité — 13 novembre 2026

## Portée validée dans la chaîne de PR

Cette revue couvre la chaîne de travail non fusionnée :
- PR #103 : stockage externe des checkpoints d'audit ;
- PR #109 : interface serveur stable utilisée par l'adaptateur ;
- PR #110 : durcissement SQL de la RPC d'ancrage ;
- PR #113 : signatures Ed25519 et cycle de vie des clés ;
- PR #114 : migration versionnée et rollback protégé ;
- PR #115 : tests d'intégration de l'adaptateur et des signatures.

Les PR restent des brouillons ouverts. La chaîne n'est pas fusionnée et ne doit pas être considérée comme déployée.

## Preuves automatisées

Sur le SHA testé de PR #115, `995cbf51d4d6375b685f6f259b609027e20b4f6b` :
- 259 tests Python réussis ;
- validation des registres réussie ;
- vérification documentaire réussie ;
- tests SQL PostgreSQL jetable réussis, y compris migration up répétée, rollback propre, réinstallation et refus atomique du rollback avec données ;
- les trois workflows requis sont réussis sur ce SHA exact.

Le test de rollback avec données produit volontairement une erreur SQL contrôlée. Le script CI vérifie que cette erreur est attendue et que les preuves et fonctions restent présentes ; elle ne représente pas un échec du workflow.

## Couverture de sécurité renforcée

- Ed25519 : signature, vérification, rotation avec conservation des anciennes clés publiques et révocation.
- Chaîne externe : contrôle des digests, liens précédents, ordre des séquences, signature et cohérence avec le journal local.
- Adaptateur Supabase : lecture après écriture, CAS, conflit, réponse perdue après commit et reprise idempotente du même enregistrement.
- Altération : un enregistrement dont la signature est falsifiée est rejeté même si son digest de contenu est recalculé.
- Migrations : installation transactionnelle, réapplication, rollback si les tables sont vides et refus de suppression lorsqu'une preuve existe.
- Worker/queue : les protections d'authentification, approbation et fencing restent couvertes par les tests existants des branches correspondantes ; ces tests ne prouvent pas l'exécution exactement une fois.

## Limites et conditions avant production

1. **Aucune vérification Ed25519 dans la RPC SQL.** La base vérifie le digest et l'enveloppe ; la vérification de signature est faite par le backend indépendant. Il faut maintenir cette frontière explicite.
2. **Keyring local uniquement.** Les fichiers privés PEM ne sont pas chiffrés par mot de passe et le modèle n'est pas multi-instance. Un KMS/HSM ou un service de signature isolé, avec audit et contrôle d'accès, est requis avant production.
3. **Transport Supabase simulé pour les tests de PR #115.** Les tests prouvent la composition et les réponses applicatives, pas l'authentification, les politiques d'une instance réelle, la disponibilité ou la résilience réseau de Supabase.
4. **Pas de runner/ledger de migration de production dans le dépôt.** L'environnement de déploiement devra enregistrer et vérifier versions et checksums, puis exécuter les migrations selon un processus approuvé.
5. **Pas d'exactly-once.** Les leases, tentatives durables, idempotency et fencing réduisent les doubles effets et les reprises périmées ; une panne après effet externe mais avant confirmation peut encore nécessiter une réconciliation métier.
6. **Gouvernance multi-agent et sécurité opérationnelle.** Les règles de délégation, permissions, identité et approbation doivent être intégrées et vérifiées dans une chaîne de livraison unique. Les PR séparées et non fusionnées ne constituent pas une preuve de déploiement cohérent.
7. **Aucune validation sur environnement réel.** Aucun secret réel, aucun worker actif, aucune migration de production et aucun déploiement n'ont été utilisés.

## Décision

**Résultat : chaîne de tests CI réussie, mais système non autorisé pour la production.**

Étapes restantes : revue de sécurité indépendante, intégration ordonnée des PR, validation d'un KMS/HSM, authentification workload, ledger/runner de migration approuvé, tests sandbox Supabase, politique de révocation et audit transactionnel, puis exercice de reprise et de réconciliation des effets externes.


## Jour 1 de la phase suivante — vérification au niveau de l'adaptateur

L'adaptateur Supabase exige désormais un callback `verify_signature` non optionnel à sa construction. Avant tout `put_record`, il valide les octets canoniques, le schéma, l'identifiant du journal et la signature. Avant le RPC CAS, il revalide le record et impose que `previous_record_digest` corresponde exactement au digest attendu. Une utilisation directe de l'adaptateur ne peut donc plus contourner la vérification faite par le service de publication.

Le validateur partagé est exposé comme contrat public `validate_signed_checkpoint_record`. Les tests d'intégration injectent le vérificateur du keyring Ed25519 local. Les tests unitaires couvrent l'absence de vérificateur au constructeur, la signature falsifiée et le lien précédent incorrect.

Limites : le callback doit être fiable et administré côté backend; le keyring local reste un mécanisme de référence, pas un KMS/HSM. La lecture des records reste disponible sans callback de vérification, mais les lectures ne constituent pas une preuve de confiance tant qu'elles ne passent pas par `verify_checkpoint_anchor`. Aucun service Supabase réel n'est appelé.
