# Mission 169 — Formulaire de fiche KDP sur iPhone

## Livrable
- Ajoute au tableau de bord un formulaire mobile pour titre, auteur, description, langue, mots-clés, catégories, tranche d'âge, droits, territoires, ISBN, éditeur, marketplace, devise et prix.
- Charge le dernier brouillon sauvegardé depuis l'API de statut.
- Enregistre les brouillons via l'endpoint versionné, avec un jeton KDP distinct.
- Affiche le numéro de version et les blocages de validation.
- Aucun champ auteur, description, catégorie, prix ou ISBN n'est inventé ; les champs inconnus restent vides.
- Les champs de formulaire sont construits sans injection HTML ; le jeton reste en mémoire de page et n'est pas persisté.

## Limites
Le formulaire permet de préparer une fiche, pas de la publier. La validation propriétaire et le release gate restent obligatoires.
