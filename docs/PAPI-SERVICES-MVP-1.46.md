# PAPI SERVICES MVP 1.46

## Objectif
Suivre une activité de services sans stock : demande qualifiée → devis → prestation → paiement documenté.

## Périmètre
Le module runtime/papi_core/services_mvp.py analyse des instantanés fournis par un opérateur.
Il produit un entonnoir commercial, les enregistrements rejetés et les recettes reconnues.
Tous les montants sont exprimés en XOF.

## Modèle de données
- Demande : identifiant, code de service, résumé expurgé, statut et date.
- Devis : demande liée, montant, date de validité et statut.
- Prestation : devis lié, statut et dates de réalisation.
- Paiement : prestation liée, montant et statut de preuve.

Les champs non autorisés sont rejetés. Les données personnelles, coordonnées, conversations
brutes, secrets et informations de paiement sensibles ne doivent pas être transmis.
Un devis enregistré n'est pas automatiquement envoyé ; une acceptation enregistrée n'est pas
une signature ou un engagement juridique.

## Reconnaissance du chiffre d'affaires
Seuls les paiements au statut provider_verified, accompagnés d'une référence, d'un vérificateur
et d'une date, sont inclus dans recognized_xof. Cette valeur est une attestation fournie en entrée :
le module ne se connecte pas au prestataire et ne vérifie pas lui-même la transaction.
Un contrôle humain sur la source de paiement reste obligatoire. Les paiements déclarés restent exclus.

## Sécurité
Lecture seule : aucun envoi, publication, appel réseau, inscription, contrat ou opération financière.
Budget : 0 XOF. Toute action externe ou financière nécessite une autorisation humaine explicite.

## Tests
Neuf tests unitaires sont fournis dans tests/test_services_mvp.py. Ils ne sont pas réputés exécutés
tant qu'un environnement de test n'a pas confirmé leur réussite.
