# PAPI GLOBAL WORK — pipeline consolidé

## Mission 17 — Jour 5/5

Le module papi_core.global_work_pipeline assemble les fondations des jours précédents :

1. Adaptateurs RSS/JSON en lecture seule : payloads fournis par une source autorisée.
2. Dédoublonnage prudent et contrôle de complétude.
3. Vérification de fraîcheur à partir d'une date avec fuseau horaire.
4. Contrôle pays, paiement, frais, KYC, politique IA et estimation du net.
5. Orientation vers une revue humaine, sans approbation ni action externe.

## États de sortie
- ready_for_human_review : tous les contrôles de données et de fraîcheur sont satisfaits ; cela n'est pas une approbation.
- hold_for_review : données absentes, offre périmée, blocage ou information à examiner.

## Limites
- Le pipeline ne récupère aucun flux sur Internet. Les adaptateurs analysent seulement les payloads fournis.
- Les URLs de preuve ne sont pas visitées ni authentifiées.
- Aucune devise n'est convertie et aucune disponibilité de paiement au Sénégal n'est présumée.
- Aucune candidature, inscription, communication, dépense ou transaction n'est effectuée.
- Les sorties restent des candidats non qualifiés ; une personne doit vérifier les preuves et décider.

La mission 17 livre ainsi une chaîne de préqualification technique, pas encore un service autonome de recherche ou de candidature.
