# Mission 74 — Kit de production local PAPI KIDS

## Objectif
Passer du catalogue de contrôle (Mission 73) à un dossier de travail reproductible pour chaque titre, sans publier ni appeler de plateforme externe.

## Livrables
1. Générateur local de dossiers de production non destructif.
2. Brief éditorial vierge et canevas de manuscrit.
3. Métadonnées de travail en JSON.
4. Checklist de production et rapport qualité initial en attente.
5. Commande CLI `kids-init`.
6. Tests de sécurité : validation des entrées, identifiants, tranche d'âge, destination symbolique, non-écrasement et absence de fausse approbation.
7. Documentation et roadmap actualisées.

## Garde-fous
- Aucun écrasement d'un dossier existant.
- Refus des chemins symboliques dans la destination.
- Identifiants de livre strictement validés.
- Aucun accès réseau, compte KDP, secret, paiement ou publication.
- Aucun fichier de projet ajouté au catalogue automatiquement.
- Les documents générés sont des modèles vierges, pas des livres terminés.
- La revue humaine et la vérification des droits restent obligatoires.

## Hors périmètre
Pas de génération IA de manuscrit/illustration, pas d'export PDF final, pas de soumission KDP, pas d'activation d'agents ou de workers.

## Critères d'acceptation
- Une création valide génère un kit de six fichiers.
- Un identifiant déjà utilisé ne remplace jamais un dossier existant.
- Les entrées invalides et destinations symboliques sont refusées.
- Les tests unitaires et les workflows CI passent sur le SHA final.
