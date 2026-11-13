# PAPI GLOBAL WORK — contrôle des preuves

## Fonctionnement
Le module \`papi_core.global_work_evidence\` analyse des observations déjà fournies par un réviseur humain. Il valide le format des preuves, normalise les URL HTTPS publiques, contrôle les dates, puis compare les observations par champ.

Champs contrôlés : pays admissibles, moyens de paiement, frais, politique IA et conditions d'utilisation.

## Résultats
- \`human_review_required\` : observations récentes et cohérentes ; elles ne sont pas certifiées par le logiciel.
- \`contradiction_detected\` : plusieurs observations d'un même champ se contredisent.
- \`insufficient_evidence\` : preuves absentes, périmées ou datées dans le futur.

Une preuve ancienne ou future ne suffit pas à établir un fait actuel. Les valeurs contradictoires sont conservées pour examen, jamais arbitrées automatiquement.

## Limites de confiance
- Les URL sont enregistrées mais jamais ouvertes.
- Le module ne vérifie ni l'authenticité de la page, ni son auteur, ni son contenu.
- Le nom du réviseur est une déclaration fournie en entrée, pas une identité authentifiée.
- \`verified\` reste toujours \`false\` dans ce module.
- Aucun pays, paiement ou droit d'accès n'est inféré.
- Aucun appel réseau, inscription, candidature, message, dépense ou transaction n'est exécuté.

La validation finale doit être effectuée par une personne qui consulte directement les conditions officielles de la plateforme.
