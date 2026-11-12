# PAPI AGENT WORKFLOW ENGINE 1.22

## Objectif
Préparer des plans multi-agents déterministes avec dépendances, ordre topologique et contrôles qualité.

## Contrôles
- Créateur actif, profil complet et permission explicite `create_agent_workflows`.
- Chaque exécutant et réviseur doit être présent, actif/déployé et avoir un profil complet.
- Réviseur distinct de l'exécutant.
- Dépendances existantes, uniques et sans cycle ; ordre topologique stable.
- Critères d'acceptation obligatoires et preuve requise avant toute validation qualité.
- Événements de proposition projetés depuis le journal d'audit ; doublons rejetés.

## Limites de cette phase
Le moteur ne crée ni tâche, ni affectation, ni message, ni notification. Il ne démarre aucun worker, n'écrit pas dans le journal, n'appelle aucun service externe et ne dépense rien. L'approbation est une métadonnée ; l'authentification cryptographique du runtime et l'approbation effective du propriétaire restent absentes.

Les 40 identités actuelles sont planifiées/incomplètes : elles ne satisfont donc pas les critères d'activation. Cette phase constitue du code proposé, pas un moteur déployé.

## Vérification
Tests ajoutés dans `tests/test_agent_workflows.py`. Leur exécution et les contrôles CI doivent être vérifiés séparément.
