# Mission 52 — Plan d'exécution

| Jour | Travail | Résultat attendu |
|---|---|---|
| 1 | Audit des champs AAD et du parseur de manifeste | Modèle de menace et contrat v2 |
| 2 | AAD v2 avec horodatage et tailles | Métadonnées critiques authentifiées |
| 3 | Validation stricte du manifeste | Rejet des types, tailles et champs inattendus |
| 4 | Compatibilité v1 et tests de falsification | Régression couverte |
| 5 | Documentation, rapport, CI et revue finale | PR prête à revue, jamais fusionnée automatiquement |

## Risques contrôlés
- Compatibilité : conserver explicitement le chemin AAD v1.
- Corruption : vérifier SHA-256 et taille avant authentification GCM.
- Ambiguïté JSON : ensemble de clés exact et types stricts.
- Secrets : clés uniquement locales, jamais dans GitHub.
