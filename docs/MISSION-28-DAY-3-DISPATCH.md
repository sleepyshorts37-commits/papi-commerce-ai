# Mission 28 — Jour 3 : distribution des tâches

`papi_assign_worker_task` vérifie atomiquement que le worker est actif, possède la compétence et la permission demandées, et dispose de capacité. Il crée un job interne et une affectation dans la même transaction. L'unicité partielle interdit deux affectations actives d'une même tâche. La clé d'idempotence retourne l'affectation initiale.
