# Mission 35 — Plan d'exécution

| Jour | Lot | Preuve |
|---|---|---|
| 1 | Audit du registre et de la documentation organisationnelle | Inventaire de 40 profils et divergence Ndeye/Oumou identifiée |
| 2 | Règles canoniques d'identité et de nommage | Document de gouvernance |
| 3 | Validateur Unicode et règles de cohérence | Fonction testable et résumé par département/statut |
| 4 | Tests, CLI et CI | Cas positifs/négatifs et contrôle obligatoire dans Actions |
| 5 | Documentation, rapport et vérification finale | PR draft, SHA exact et CI verte |

## Critères d'acceptation
- Tous les IDs sont uniques et valides.
- Les noms affichés sont uniques après normalisation Unicode.
- Les fonctions, départements, statuts, permissions et interdictions sont valides.
- Les responsables hiérarchiques optionnels pointent vers un agent connu.
- La commande retourne un code non nul si le registre est incohérent.
- Le registre existant reste à 40 agents, sans activation ni création implicite.
- Tests et CI réussissent sur le SHA final.
