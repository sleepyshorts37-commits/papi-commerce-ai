# Mission 163 — Revue de sécurité depuis l'iPhone

## Livrable
- Le tableau de bord mobile affiche les alertes de sécurité par page, leur gravité et l'extrait concerné.
- Affiche l'état de la revue précédente et détecte une attestation périmée si le hash du manuscrit a changé.
- Permet approuver/refuser avec notes, directement depuis iPhone.
- Utilise un champ secret distinct pour \`PAPI_KIDS_SAFETY_REVIEW_TOKEN\`, jamais stocké par l'interface.
- Envoie le SHA-256 exact de l'analyse au endpoint persistant ; le backend attribue le réviseur et crée la preuve.
- Les approbations avec alertes exigent au moins 20 caractères de justification.
- DOM construit avec \`textContent\` pour éviter l'injection HTML des extraits du manuscrit.

## Gouvernance
L'écran ne modifie pas le manuscrit et ne lance aucun fournisseur IA/image. L'approbation ne publie rien.
