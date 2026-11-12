# PAPI SALES ENGINE 1.48

## Objectif
Fournir un pipeline CRM minimaliste pour suivre les prospects PAPI SERVICES, prioriser les relances et mesurer les conversions commerciales.

## Fonctionnement
`analyze_sales_pipeline(records, as_of=None)` valide un instantané de 500 prospects maximum, élimine les identifiants dupliqués et retourne :
- le nombre de prospects par statut ;
- les relances en retard ou à effectuer aujourd'hui ;
- les prospects sans mise à jour depuis au moins sept jours ;
- le nombre de ventes gagnées/perdues et le taux de gain parmi les dossiers clôturés ;
- les enregistrements rejetés avec leur index et le motif.

Statuts admis : `new`, `qualified`, `contact_approved`, `contacted`, `interested`, `quote_prepared`, `won`, `lost`, `disqualified`.

## Données minimales et confidentialité
Le registre accepte uniquement un identifiant interne, une source, un secteur, un résumé non sensible du besoin, un statut, un code de service, un responsable et des dates. Les noms, numéros, e-mails, identifiants sociaux et autres coordonnées personnelles sont interdits.

## Limites et sécurité
- Module local et en lecture seule : aucune navigation web, prospection, publication, prise de contact, relance automatique ou transaction.
- `contact_approved` est une étiquette de suivi uniquement ; elle ne déclenche ni n'autorise techniquement un envoi.
- Le taux de gain est une mesure CRM, pas une preuve de paiement ni un chiffre d'affaires encaissé.
- Toute prise de contact et tout engagement commercial nécessitent un processus séparé et une validation humaine.
- Budget : 0 XOF. Aucun abonnement ou service payant.
- Tests ajoutés mais non exécutés dans le cadre de cette livraison.
