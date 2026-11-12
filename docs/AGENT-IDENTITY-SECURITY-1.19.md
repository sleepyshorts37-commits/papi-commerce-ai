# PAPI AGENT IDENTITY & SECURITY 1.19

## Contrôles ajoutés
- Validation du schéma des fiches d'identité.
- Unicité des identity_id et agent_id.
- Empreinte SHA-256 canonique d'une fiche pour détecter une modification.
- Comparaison d'empreinte attendue.
- Autorisation fail-closed : identité intègre, agent lié au registre, profil complet, agent actif et permission explicitement accordée.
- Toute permission absente ou interdite est refusée.

## Limites importantes
Une empreinte SHA-256 n'est pas une signature numérique : elle ne prouve pas qui a créé ou présenté la fiche. L'authentification runtime nécessite une clé privée protégée, une signature vérifiée et une gestion sûre des clés. Cette phase ne prétend pas fournir cette authentification.
Le contrôle d'approbation du propriétaire est séparé et n'est pas réalisé ici. Une décision allow est un résultat de politique, pas l'exécution d'une action.

## Garde-fous
Lecture seule. Aucun changement de fiche, permission, statut, affectation ou autonomie. Aucun secret n'est stocké. Aucun worker, agent ou action externe n'est lancé.

## État du registre actuel
Les fiches existantes sont principalement planned et profile_state=incomplete. Elles seront donc refusées pour toute autorisation opérationnelle jusqu'à leur complétion et activation contrôlée.
Tests ajoutés ; exécution et CI à vérifier séparément.
