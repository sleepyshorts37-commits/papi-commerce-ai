# Gouvernance des identités et contrôle de l'organigramme

## Référentiel de vérité
`data/agents.json` est la source canonique des identifiants, noms affichés, fonctions, départements, statuts, permissions et interdictions. `docs/ORGANISATION.md` décrit la structure et les responsabilités, sans pouvoir accorder des permissions.

## Règles
1. L'identifiant technique est stable, unique et limité aux caractères minuscules ASCII, chiffres, tiret et underscore.
2. Le nom affiché est non vide et unique après normalisation Unicode (casse, accents, espaces).
3. Les fonctions et départements sont obligatoires.
4. Le statut appartient à `defined`, `planned`, `active`, `suspended` ou `revoked`.
5. Les permissions et interdictions sont des listes de chaînes non vides, sans doublon.
6. Un responsable hiérarchique optionnel référence un identifiant existant.
7. Un changement de nom, de fonction, de département ou de responsable doit être explicite, auditable et répercuté dans la documentation.
8. Un agent défini ou planifié n'est pas considéré comme déployé.

## Clarifications appliquées
- `ndeye` : prospection LinkedIn.
- `oumou-rh` : ressources humaines numériques.
- `cheikh-prospect` : prospection par e-mail.
- `cheikh-fall` : fiabilité et surveillance technique.

Ces identifiants différents ne doivent pas être confondus. Aucune nouvelle identité n'a été créée par la mission.

## Contrôle automatique
`PYTHONPATH=runtime python -m papi_core organization-check`

La commande retourne le nombre d'agents, les effectifs par département et statut, et les erreurs de validation. Elle n'affiche aucune permission secrète, n'active aucun agent et ne contacte aucun service externe.

## Limites
Le contrôle prouve la cohérence structurelle du registre uniquement. Il ne prouve pas l'existence d'une personne, une validation RH, une délégation légale, une authentification ou un déploiement opérationnel. L'approbation finale de l'organigramme demeure une décision du propriétaire.
