# PAPI GLOBAL WORK — sources et ingestion

## Objectif du Jour 1/5

Poser un contrat d'ingestion commun pour les sources de missions rémunérées, avec provenance, dédoublonnage et refus par défaut des sources non autorisées.

## État livré

- Registre versionné `data/global-work-sources.json`.
- Types de sources prévus : API officielle, flux RSS et import manuel.
- Politique d'accès explicite : `allowed`, `owner_review` ou `prohibited`.
- Source inactive par défaut ; aucune source n'est préautorisée.
- Module `global_work_sources.py` validant le registre et les lots déjà collectés.
- Provenance conservée pour chaque opportunité acceptée : source, type, URL des conditions, horodatage et mode d'ingestion.
- Rejet des identifiants en doublon et des enregistrements invalides.

## Sécurité

Ce module ne fait aucune requête HTTP, aucun scraping et aucune authentification. Il ne reçoit que des données pré-collectées via un canal qui devra être autorisé séparément. Une source désactivée, interdite ou en revue propriétaire est bloquée. Aucun token, mot de passe, cookie, OTP, PIN ou secret API ne doit être ajouté au registre.

L'acceptation technique d'une opportunité ne prouve ni son admissibilité au Sénégal, ni l'éligibilité du compte, ni la compatibilité du paiement, ni la permission d'utiliser l'IA. Ces contrôles restent requis avant toute candidature. Aucune candidature n'est envoyée.

## Contrat de lot

Chaque lot contient un identifiant de source, un horodatage ISO-8601 avec fuseau et des enregistrements respectant le schéma canonique de `global_work.py`. Le résultat sépare les entrées acceptées et rejetées, conserve leur provenance et déclare explicitement qu'aucune action externe n'a été effectuée.

## Suite prévue

- Jour 2 : connecteurs en lecture seule pour formats de flux/API documentés, après validation des conditions et sans contourner authentification ou restrictions.
- Jour 3 : contrôles de qualité, fraîcheur, expiration et rapprochement des opportunités.
- Jour 4 : rapport de qualification Sénégal, moyens de paiement et rentabilité nette.
- Jour 5 : tests de bout en bout, audit des refus et PR/CI.

## Commande

Les tests sont exécutés par la suite de tests Python du dépôt. Le module n'est pas un service permanent et ne collecte pas de données en arrière-plan.
