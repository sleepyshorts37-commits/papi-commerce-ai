# Mission 28 — Jour 5 : validation et clôture

Les tests couvrent l'enregistrement dormant, l'activation explicite, l'affectation idempotente, les permissions, la tâche déjà attribuée, le claim et le rejet d'une complétion par un autre worker. Le moteur ne déclenche aucun effet externe. La validation finale dépend de la CI sur le SHA exact. La hiérarchie est stockée mais sa modification demeure réservée au backend de confiance.
