# Architecture technique cible

## Composants
1. Interface de commande et validation du propriétaire.
2. Orchestrateur : distribution des tâches, permissions, échéances et reprises.
3. Agents spécialisés : mission, outils autorisés, entrées, sorties et critères de qualité.
4. Registre : prospects, partenaires, missions, commandes, commissions, incidents et journaux.
5. PAPI CHAT : messages, groupes, historique et escalades.
6. Surveillance : disponibilité, échecs, quotas, coûts, retards et alertes.
7. Rapports quotidiens/hebdomadaires distinguant faits vérifiés et estimations.

## Exécution persistante
GitHub conserve le code et les versions ; il ne fait pas fonctionner à lui seul des agents en continu. GitHub Actions exécute des workflows déclenchés ou planifiés dans ses limites, mais ne remplace pas un serveur permanent ni un accès modèle gratuit illimité.

Un système persistant exige un environnement d'exécution, un ordonnanceur, une base de données, des intégrations autorisées et un fournisseur de modèle. Les offres gratuites ont des quotas et peuvent changer. Chaque composant doit être validé avant toute promesse de continuité.

## Multi-engine
Pour chaque mission critique : outil principal, méthode ou outil de secours, contrôle qualité indépendant et journal des erreurs. Le secours ne contourne jamais une limite de plateforme ou une permission refusée.

## Sécurité
Permissions minimales, séparation des environnements, secrets dans un coffre ou variables sécurisées, validation humaine des actions sensibles, limites de débit, déduplication, sauvegardes et politique de conservation. Aucun appel payant sans autorisation.

## État
Cible documentaire uniquement. Aucun orchestrateur, agent autonome, base de données, webhook, messagerie ou tâche planifiée n'est déclaré opérationnel.
