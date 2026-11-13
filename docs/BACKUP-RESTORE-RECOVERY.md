# Sauvegarde, restauration et reprise après incident

## État réel

Le dépôt dispose d'un adaptateur Supabase, d'un schéma SQL et de tests simulés. Aucun projet Supabase distant n'est connecté et aucun mécanisme de sauvegarde/restauration de données métier n'est opérationnel. Cette PR ajoute uniquement une validation locale de manifestes et un plan de restauration descriptif.

## Contrat du manifeste

Chaque manifeste doit identifier la sauvegarde, sa source, l'horodatage UTC, la version du schéma et la durée de rétention. Chaque artefact possède un chemin relatif sûr, un type, une taille en octets et une empreinte SHA-256. Le validateur exige une correspondance exacte entre les artefacts déclarés et les contenus fournis, puis vérifie taille et empreinte.

Le validateur refuse les chemins absolus, les segments `.`/`..`, les doublons, les payloads manquants ou supplémentaires, les dates non UTC et les rétentions hors plage (1 à 3650 jours).

## Procédure recommandée (à exécuter uniquement en environnement isolé)

1. Identifier la source, la version du schéma, le périmètre des données et le responsable.
2. Produire une sauvegarde via un outil approuvé du fournisseur, avec chiffrement au repos et en transit.
3. Générer un manifeste signé par un mécanisme de confiance distinct du contenu sauvegardé.
4. Stocker la sauvegarde dans un emplacement séparé, à accès restreint, avec versionnement et journalisation.
5. Vérifier périodiquement les empreintes et effectuer un exercice de restauration sur une base jetable isolée.
6. Comparer le nombre d'enregistrements, les contraintes, les relations, les permissions et les contrôles d'intégrité.
7. Documenter le RPO/RTO réellement mesuré, les écarts et l'approbation du responsable avant toute restauration réelle.

## Rétention et sécurité

- Définir la rétention selon les obligations légales, la minimisation des données et les besoins métier ; la valeur du manifeste n'autorise pas à elle seule une suppression.
- Chiffrer les sauvegardes contenant des données personnelles ou commerciales et séparer les clés des fichiers.
- Ne jamais inclure de clés API, tokens, mots de passe ou secrets dans un manifeste, une archive ou les logs.
- Restreindre les accès, tracer les consultations et tester la révocation.
- Appliquer une règle de conservation hors ligne/immuable si le fournisseur et le coût le permettent.
- Toute purge, copie distante ou restauration exige une procédure approuvée et un opérateur humain.

## Limites explicites

Le module `papi_core.backup_restore` ne crée pas d'archive, ne contacte aucun fournisseur, ne chiffre ni ne signe, ne supprime rien et n'écrit aucune donnée. `build_restore_plan` ne fait qu'émettre un plan après vérification d'intégrité. Aucune migration ni restauration sur une base réelle n'est permise par cette étape.

Avant production : choisir le fournisseur et la stratégie de sauvegarde, définir RPO/RTO, intégrer chiffrement et signature gérés, vérifier les droits et la rétention, tester les restaurations complètes sur infrastructure jetable, puis faire approuver un exercice contrôlé.
