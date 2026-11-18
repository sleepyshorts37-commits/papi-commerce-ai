# Revue de sécurité ciblée — 14 novembre 2026

## Périmètre et méthode

Revue statique des sources de la branche d'intégration de la PR #97, avec vérification des exécutions GitHub Actions associées au SHA `2c3a126b962978246b6219b97c48be10f0657a8f`. Les tests locaux et les essais sur une infrastructure déployée n'ont pas été exécutés dans le cadre de cette revue. Ce document ne constitue ni un audit indépendant certifié ni un test d'intrusion.

## Résultats

### 1. Attribution des refus après authentification — correction proposée dans la PR #98

**Constat :** `authorize_authenticated_agent()` vérifiait la signature et l'anti-rejeu, puis appelait `authorize_agent()`, qui applique également les permissions métier et peut lever `AccessDenied`. Le worker classait ce refus comme un échec d'authentification et l'attribuait au worker système, alors que l'identité cryptographique était déjà vérifiée.

**Correction proposée :** créer un principal scellé après vérification cryptographique, distinguer explicitement le refus de politique post-authentification avec `AuthenticatedAuthorizationDenied`, puis attribuer l'événement `job.blocked` à l'agent vérifié. Une régression vérifie le code `permission_denied`, l'acteur et l'absence d'appel au handler.

**Statut au 18 novembre :** implémenté dans les PR #98 et #99. Les SHA courants #98 (`e9b7b97bf8a09b96d893b04880fd9ebcf4591e15`) et #99 (`de6f6884871790c93ca42612c6cd8a69e1c3631a`) ont chacun les trois workflows CI réussis, avec 233 et 234 tests core respectivement. Aucune revue indépendante n'est enregistrée. La version worker de l'ancienne branche #102 n'interceptait pas encore `AuthenticatedAuthorizationDenied` avant `AccessDenied` ; la nouvelle branche d'intégration corrige cet ordre.

### 2. Chaîne d'audit locale

**Protections observées :**
- Sérialisation canonique et chaînage SHA-256.
- Vérification complète avant lecture et ajout.
- Déduplication des identifiants d'événement.
- Verrou inter-processus POSIX, écriture append et `fsync`.
- Refus des liens symboliques pour les fichiers journal/verrou, des fichiers non réguliers et des permissions trop ouvertes.
- Checkpoints capables de détecter une réécriture ou un retour en arrière par rapport à un checkpoint connu.

**Limites :**
- Le verrouillage repose sur `fcntl` : cette implémentation n'est pas portable vers Windows natif et ne fournit pas à elle seule une coordination multi-hôte.
- La chaîne locale ne protège pas contre un attaquant capable de réécrire simultanément le journal et les checkpoints locaux.
- La création des répertoires parents n'établit pas à elle seule une frontière de confiance sur toute l'arborescence.
- Les événements terminaux sont volontairement best-effort après la transition durable de la file ; une panne d'audit à ce stade peut donc laisser une transition sans événement terminal local.
- L'identifiant d'événement worker doit être calculé à partir de `job_id + attempt_id + action` : deux tentatives d'un même job restent distinctes, tandis qu'une répétition dans une tentative reste dédupliquée. La branche d'intégration du 18 novembre relie les événements au UUID durable de réservation.

### 3. Ancrage externe

**État réel :** le dépôt contient un contrat `CheckpointStore`, une publication avec insertion immuable et compare-and-swap, une vérification de chaîne et des tests utilisant un magasin en mémoire.

**Non réalisé :**
- Aucun fournisseur externe réel n'est branché.
- Aucune durabilité indépendante n'est démontrée.
- Aucun service de signature géré ni coffre de clés externe n'est configuré.
- Le pointeur `latest` doit être protégé par les garanties réelles du fournisseur et, pour la détection de rollback, par une source de confiance indépendante ou un mécanisme de transparence vérifiable.

**Décision :** considérer l'ancrage comme prototype de contrat seulement, pas comme protection externe opérationnelle.

### 4. Identité et anti-rejeu

Le worker accepte le chemin Ed25519 versionné et le chemin HMAC historique. Le contrôle de signature est lié à l'agent, à la permission, à la tâche et au handler ; le nonce est consommé dans SQLite. Le registre Ed25519 contient l'état et la version de clé.

**À valider avant production :**
- Concurrence réelle entre plusieurs processus/instances lors de la rotation et de la révocation.
- Sauvegarde et récupération du registre public et des éléments anti-rejeu.
- Gestion des clés privées et rotation avec une frontière de secrets adaptée à l'hébergement.
- Conservation du matériel public historique nécessaire pour vérifier les checkpoints signés antérieurs.

### 5. Worker et file d'exécution

**Protections observées :**
- Désactivé si `execution_enabled` n'est pas exactement `true`.
- Handler choisi dans un registre de confiance, jamais importé depuis le payload.
- Validation stricte de l'approbation avant authentification.
- Authentification avant autorisation générale.
- Renouvellement du bail et écriture durable de `job.handler_started` avant le handler.
- Le handler ne démarre pas si cette écriture d'audit échoue.
- Réservation, renouvellement, complétion et échec délégués à des RPC Supabase avec jeton de bail.

**À valider avant production :**
- Idempotence des effets métier après crash entre effet et confirmation.
- Fencing lorsque le handler dure plus longtemps que le bail ou ignore `ensure_lease`.
- Comportement sous concurrence multi-worker et perte réseau pendant `complete` / `fail`.
- S'assurer que tout handler ayant un effet externe appelle le contrôle de bail immédiatement avant cet effet ; le callback fourni au handler ne garantit pas qu'il sera utilisé.

## CI et état des PR vérifiés le 18 novembre 2026

Les PR #85, #94, #95, #96, #97, #98, #99, #100, #101 et #102 sont ouvertes et en brouillon. Les trois workflows core, registre et documentation ont une conclusion `success` sur les SHA de tête observés. Aucune revue indépendante n'est enregistrée ; la PR #95 contient un commentaire de coordination sur l'ordre d'autorisation.

| PR | SHA de tête | Base | Mergeable |
|---|---|---|---|
| #85 | `f39fe15040448858d72d81ed4bab676f6b3b294a` | `main` | true |
| #94 | `f4e07d7b9d14f20cfe454249112663187257d232` | `main` | true |
| #95 | `ce55f1611338facde9fd74943a84c550d89933f0` | `main` | true |
| #96 | `7bbeab5650397beda42d3fadac391b8628988e31` | `hardening/audit-hash-chain` | true |
| #97 | `0b7da99997f4179c5ccf7556b96969ce6d60c0aa` | `main` | true |
| #98 | `e9b7b97bf8a09b96d893b04880fd9ebcf4591e15` | `integration/security-approval-audit-2026-11-13` | true |
| #99 | `de6f6884871790c93ca42612c6cd8a69e1c3631a` | `security/worker-authz-attribution-2026-11-14` | true |
| #100 | `54d8bc8f1858af69baa8792c192ee82b68addb02` | `main` | true |
| #101 | `3e80fa406c3c44e8c53b758fd8f8e4c12ecbb569` | `main` | true |
| #102 | `98d506a278d6617ffc42917c0d82382b67376af5` | `feat/durable-job-attempt-ids-2026-11-17` | false |

Sur #101, le core a exécuté 215 tests et les étapes PostgreSQL 16 jetables — schéma, fixtures legacy, migration, UUID distincts, expiration, reprise, statuts, épuisement et rollback — ont toutes réussi.

La PR #102 est divergente de la tête actuelle #101 : 48 commits en avance et 6 en retard par rapport au point commun `4f529a97fd6d7f613c38af7df15307a0c7e575fd`. Ne pas la fusionner en l'état. Une branche d'intégration distincte a été créée depuis le SHA courant #101. Les trois workflows utilisent `pull_request:` sans filtre limité à `main`, et les exécutions sur les PR empilées confirment que leurs bases non-`main` sont validées.

## Priorités de sortie

1. Exécuter la CI complète sur la PR #98 et corriger toute régression.
2. Faire relire indépendamment le découpage authentification / autorisation / attribution d'audit.
3. Ajouter une identité d'essai durable pour les événements de tentative worker.
4. Définir puis tester un adaptateur d'ancrage sur un vrai service indépendant dans un environnement de test, sans secret en dépôt.
5. Tester les scénarios de crash et d'idempotence de handlers avec PostgreSQL/Supabase de test.
6. Conserver les actions financières, communications externes, déploiements et workers désactivés jusqu'à revue formelle et autorisation distincte.

## État de gouvernance

Aucune modification de `main`, fusion, mise en production, activation d'agent/worker, communication externe ou opération financière n'a été effectuée.
