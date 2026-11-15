# Mission 122 — Intégration du registre à PAPI KIDS

## Résultat
L'orchestrateur PKP-0001 expose désormais \`prepare_pkp0001_campaign_from_registry\`. Il demande au registre gouverné de choisir un modèle admissible pour les 24 illustrations, puis construit le plan à partir du modèle, du coût et de la preuve retenus.

## Contrôles
- Aucun fournisseur non activé ne peut être choisi.
- La preuve doit correspondre au compte et au modèle sélectionnés.
- Le fournisseur doit couvrir le coût estimé de la campagne.
- Le moteur PKP-0001 refuse pour l'instant tout fournisseur autre que Cloudflare, car c'est le seul adaptateur image intégré dans ce chemin.
- Cette fonction prépare uniquement le plan : aucun appel fournisseur ni génération.
- Les réservations du ledger partagé restent exigées lors de l'exécution.

## Tests
Tests hors réseau : sélection correcte d'un modèle admissible, préparation des 24 scènes, refus si aucun modèle n'est éligible, refus si la revue commerciale manque.
