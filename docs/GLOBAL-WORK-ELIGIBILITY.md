# PAPI GLOBAL WORK — éligibilité et rentabilité

## Mission 17 — Jour 4/5

Le module papi_core.global_work_eligibility évalue les informations explicitement fournies sur une mission : pays admissibles, montant brut, devise, moyens de paiement, frais, coût initial, temps estimé, exigences KYC, règles IA et présence humaine. Il calcule le net et le net horaire uniquement lorsque les données nécessaires sont présentes.

## États
- insufficient_evidence : une ou plusieurs données essentielles manquent.
- rejected_or_manual_review : blocage détecté (pays non listé, IA interdite ou net négatif).
- ready_for_human_review : champs et références présents, sans approbation automatique.

## Garanties
- Les informations manquantes restent inconnues ; aucun pays, moyen de paiement, frais ou statut KYC n'est deviné.
- L'éligibilité pays ne prouve pas qu'un prestataire de paiement accepte le Sénégal.
- Les références de preuve doivent être vérifiées par un humain ; le module ne les consulte pas.
- Aucun taux de change, revenu garanti, inscription, candidature, dépense ou paiement.
- Aucune requête réseau. Toute mission reste non qualifiée automatiquement.
