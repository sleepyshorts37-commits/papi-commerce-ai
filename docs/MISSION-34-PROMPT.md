# Mission 34 — PAPI SUPABASE INTEGRATION & ENVIRONMENT READINESS

## Durée et périmètre
Bloc de cinq journées exécuté en une seule mission, avec réalisation réelle dans le dépôt GitHub. La mission prépare l'intégration Supabase de manière vérifiable sans toucher à un projet hébergé.

## Cahier des charges par journée

### Jour 1 — Audit des prérequis
1. Relire les contrats Supabase, le stockage PostgREST, les migrations, les adaptateurs d'identité et worker.
2. Inventorier les migrations ascendantes, leurs versions et les rollbacks présents.
3. Distinguer les validations locales, simulées et hébergées.
4. Documenter les limites de la stack locale (PostgreSQL/PostgREST ≠ Supabase Auth complet).

### Jour 2 — Contrôle statique de migration
1. Ajouter un inventaire déterministe des migrations.
2. Détecter noms invalides, versions dupliquées et séquences discontinues.
3. Calculer SHA-256 et taille de chaque migration.
4. Indiquer la disponibilité du rollback sans l'exécuter.

### Jour 3 — Préflight de configuration
1. Valider la forme de l'URL HTTPS Supabase.
2. Détecter la présence d'une clé serveur sans jamais afficher sa valeur.
3. Repérer les fichiers .env locaux non autorisés.
4. Ne créer aucun client et n'effectuer aucun appel réseau.

### Jour 4 — Intégration CLI et tests
1. Ajouter `papi supabase-preflight`.
2. Ajouter `--require-configured` pour bloquer un environnement incomplet.
3. Tester configuration absente, URL invalide, clé présente, fuite de secret, fichiers .env, migration dupliquée et trou de version.
4. Vérifier les drapeaux de sécurité qui restent désactivés.

### Jour 5 — Documentation, CI et transfert
1. Documenter l'usage et les limites.
2. Ajouter la suite de tests au workflow Python existant.
3. Exécuter tous les tests, la validation des registres et la CI.
4. Vérifier le SHA exact du dernier commit.
5. Ouvrir une PR brouillon, non fusionnée, et produire le rapport final.

## Livrables
- Module offline de préflight Supabase.
- Commande CLI et tests automatisés.
- Documentation opérateur et rapport de mission.
- Aucun secret, donnée client, connexion hébergée, migration distante, déploiement ou activation d'agent.

## Critères d'acceptation
- Inventaire déterministe, sans trou ni doublon.
- Aucune valeur secrète dans le rapport ou les exceptions.
- Zéro appel réseau.
- Les contrôles ne déclarent jamais la production prête.
- Tous les tests locaux et jobs CI réussissent sur le SHA exact.
- PR ouverte en brouillon et non fusionnée.
