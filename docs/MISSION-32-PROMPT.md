# Prompt d'exécution — Mission 32 : PAPI MULTI-INSTANCE MEMORY & CHAT SYNC

## Rôle
Agir comme ingénieur senior Python/PostgreSQL/Supabase, spécialiste sécurité applicative et systèmes multi-instances. Travailler uniquement dans le dépôt et la branche de mission. Examiner les interfaces réelles avant modification et valider chaque contrat par tests.

## Objectif
Compléter la synchronisation de PAPI MEMORY et PAPI CHAT entre plusieurs instances. Les migrations 004/005 fournissent déjà les tables append-only, les clés d'idempotence et des index de pagination, mais les modules Python mémoire et chat restent locaux. Ajouter des adaptateurs distants explicites, une pagination stable, une déduplication fiable et des contrôles de visibilité. Ne jamais prétendre qu'une instance est synchronisée tant qu'un environnement Supabase de test n'a pas été configuré et vérifié.

## Jour 1 — Audit et contrats
1. Examiner memory.py, chat.py, principal.py, identity.py, storage.py, migrations 004/005 et tests.
2. Définir les formats canoniques d'événements mémoire (remember/supersede) et messages.
3. Définir la séparation shared/agent, visibilité destinataire/all, identité authentifiée et limites du modèle de confiance service_role.
4. Choisir une pagination keyset stable, déterministe et bornée (pas OFFSET).
5. Documenter les conflits, doublons, reprise après erreur réseau et limites multi-écrivains.

## Jour 2 — Adaptateurs Supabase
1. Étendre SupabaseStore avec des opérations explicites d'ajout et de lecture pour mémoire et chat.
2. Garder les clés serveur uniquement côté serveur ; aucune clé service_role dans le navigateur.
3. Convertir les structures locales vers les colonnes SQL sans perte ni élargissement de portée.
4. Utiliser les clés d'idempotence uniques existantes ; un retry du même événement ne doit pas créer de doublon.
5. Vérifier la réponse serveur et échouer en mode fermé sur toute forme inattendue.
6. Ne pas modifier les comportements locaux par défaut ; le stockage distant doit être injecté explicitement.

## Jour 3 — Lecture, pagination et autorisations
1. Ajouter des lectures paginées par curseur stable, bornées et ordonnées sans doublon.
2. Mémoire shared visible selon la politique ; mémoire agent uniquement à son auteur et au propriétaire.
3. Chat direct visible seulement pour l'expéditeur/destinataire autorisé ; diffusion all visible pour les agents habilités.
4. Les événements supersede ne doivent jamais effacer l'historique ; l'archive est logique.
5. Rejeter les identités non authentifiées, acteurs incohérents, destinataires inconnus, portées interdites et limites invalides.
6. Les contrôles applicatifs doivent être documentés comme frontière de confiance : le rôle service_role est privilégié et ne doit être utilisé que dans un backend fiable.

## Jour 4 — Tests et intégration
1. Ajouter tests unitaires simulant PostgREST : insertion, lecture, mapping, erreurs HTTP, réponse mal formée.
2. Tester idempotence, rejeu, pagination multi-pages, curseur invalide et absence de doublons.
3. Tester l'isolation mémoire agent et les destinataires chat.
4. Ajouter migration additive seulement si un changement SQL est réellement requis ; rollback non destructif.
5. Ajouter les tests SQL aux deux parcours PostgreSQL jetables CI.
6. Exécuter l'ensemble des tests Python, SQL et PostgREST local ; corriger chaque échec.

## Jour 5 — Documentation et clôture
1. Documenter configuration serveur, contrat d'API, pagination, reprise, limites et procédure de bascule.
2. Documenter explicitement qu'aucun projet Supabase réel n'est configuré ni testé.
3. Vérifier qu'aucun secret, donnée personnelle ou vrai journal mémoire/chat n'est committé.
4. Vérifier CI sur le SHA final exact et la revue des changements.
5. Ouvrir une PR draft basée sur mission-31-shared-command-center ; ne pas fusionner.

## Gouvernance non négociable
- Ne pas modifier les rôles, missions, hiérarchie, permissions ni responsabilités des agents.
- Ne pas activer workers, scheduler, agents autonomes ou exécution permanente.
- Aucun message externe, prospection, publication, paiement, dépense, achat, transfert ou retrait.
- Aucun déploiement, migration distante ou connexion à un projet Supabase non explicitement configuré.
- Aucun secret, clé, token, OTP, PIN, CVV, donnée client ou journal réel dans GitHub.
- Le stockage local demeure le comportement par défaut ; pas de synchronisation automatique sans configuration et activation explicites.
- Ne pas fusionner la PR.
- Déclarer tout contrôle non exécuté comme non vérifié.

## Critères d'acceptation
- Adaptateurs mémoire et chat injectables, sans effet réseau implicite.
- Identité/acteur et visibilité validés ; mémoire agent isolée.
- Append-only et idempotence conservées.
- Pagination keyset stable, bornée et testée.
- Tests unitaires et CI SQL verts sur le SHA final.
- Documentation claire sur le modèle de confiance service_role et les limites de déploiement.
- PR draft, ouverte et non fusionnée.
