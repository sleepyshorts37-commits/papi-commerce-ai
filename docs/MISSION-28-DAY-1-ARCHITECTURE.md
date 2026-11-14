# Mission 28 — Jour 1 : architecture

Le worker est une identité d'exécution distincte de l'agent conversationnel. Son registre central porte département, rôle, responsable, compétences, permissions et capacité. L'état initial est toujours `registered`, non exécutable. Les tâches restent dans `papi_tasks`, les exécutions dans `papi_jobs`, les affectations dans `papi_worker_assignments`. Le backend de confiance orchestre les transitions.
