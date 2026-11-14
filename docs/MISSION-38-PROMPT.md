# Mission 38 — Contrat de synchronisation inter-instances

## Objectif
Préparer la synchronisation de PAPI CHAT et de la mémoire partagée entre instances avec un contrat déterministe, vérifiable et fail-closed. Cette mission ne connecte aucune instance distante et ne transporte aucune donnée réelle.

## Jour 1 — Audit et frontières
- Auditer journaux PAPI CHAT/mémoire, identités, mécanismes d'approbation et schéma de sync existant.
- Identifier les invariants : identité source, identifiant d'événement, ordre, intégrité, confidentialité et autorité de destination.
- Documenter ce qui est déjà implémenté et ce qui reste hypothétique.

## Jour 2 — Contrat de paquet
- Définir un paquet export/import versionné, borné en taille et canonique.
- Inclure instance source, génération, plage/curseur, empreintes et événements strictement validés.
- Exclure secrets, données client, clés privées et données restreintes.

## Jour 3 — Résolution des conflits et anti-rejeu
- Définir l'idempotence sur identifiants stables et empreintes de contenu.
- Rejeter ID déjà vu avec contenu divergent, séquence incohérente, instance inconnue et horodatage sans fuseau.
- Ne jamais écraser silencieusement un journal append-only ; quarantaine des conflits.

## Jour 4 — Sécurité et scénarios
- Formaliser authentification de l'instance, approbation liée au digest, destination et portée exacte.
- Définir tests reproductibles pour doublons, replay, altération, divergence, paquet incomplet et restauration.
- Maintenir les tests entièrement locaux et synthétiques.

## Jour 5 — Livraison
- Mettre à jour contrat, plan opérateur, feuille de route et rapport.
- Valider les tests et CI sur le SHA final.
- Ouvrir une PR brouillon non fusionnée.

## Critères d'acceptation
- Contrat explicite et versionné, fail-closed et idempotent.
- Aucun conflit ni rejeu accepté silencieusement.
- Aucune donnée réelle transmise ; aucun endpoint ou worker activé.
- Toute capacité non testée est déclarée non opérationnelle.
- CI réussie sur la tête finale de PR.

## Interdictions
Pas de connexion Supabase hébergée, migration distante, déploiement, scheduler, worker actif, synchronisation de données réelles, message externe, publication, paiement ou dépense sans autorisation explicite.