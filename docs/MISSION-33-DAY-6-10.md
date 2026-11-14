# Mission 33 — Jours 6 à 10 : planification déterministe

6. Conversion des écarts local_only et remote_only en références d'action sans contenu.
7. Exclusion des entrées identical ; aucun arbitrage automatique des conflicts.
8. Identifiants d'action reproductibles, liés au plan, à l'agent et à la destination.
9. Limite configurable de 1 à 500 actions, validation des identifiants et détection des doublons.
10. Tests des altérations, incohérences d'acteur, conflits, dépassements et absence d'écriture.

**État :** module `runtime/papi_core/sync_protocol.py` et tests `tests/test_sync_protocol.py` ajoutés dans cette mission.
