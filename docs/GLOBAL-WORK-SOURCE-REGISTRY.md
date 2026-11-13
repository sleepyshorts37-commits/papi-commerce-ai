# PAPI GLOBAL WORK — registre des sources

## Objectif
Centraliser les plateformes, job boards, marketplaces, programmes de missions et pages carrières qui peuvent fournir des pistes de travail.

## Contrat d'une source
Chaque entrée comporte un identifiant stable, un nom, une URL HTTPS publique, un type, un mode d'accès, un état de vérification, les pays admissibles et les moyens de paiement connus.

## États et activation
- \`unverified\` : simple piste. Jamais activée, même si \`enabled=true\` est demandé.
- \`verified\` : exige des preuves distinctes pour l'éligibilité pays, les modalités de paiement et les conditions d'utilisation, une date ISO-8601 avec fuseau et un réviseur humain.
- \`suspended\` : source désactivée jusqu'à nouvel examen.

Une source vérifiée n'est pas automatiquement autorisée à être interrogée. L'ingestion n'est autorisée par le résumé que si la source est vérifiée, explicitement activée et utilise \`authorized_api\` ou \`authorized_feed\`. Le module ne réalise lui-même aucune requête réseau.

## Sénégal et paiements
Une liste de pays vide signifie « inconnu », pas « accepté ». Les moyens de paiement vides signifient « non vérifiés ». Aucun support de Wave, Orange Money, PayPal, Visa ou Mastercard n'est présumé. Toute affirmation doit être reliée à une preuve consultable et datée.

## Gouvernance
- Les sources manuelles restent consultables par l'utilisateur sans automatisation.
- API et flux uniquement si l'accès est documenté et autorisé par le fournisseur.
- Pas de scraping interdit, contournement de connexion, collecte de données privées ou candidature automatique.
- Toute source reste soumise à une revue humaine ; aucun candidat n'est automatiquement qualifié.
- Les changements de conditions, de pays ou de paiement doivent déclencher une nouvelle vérification.

## Tests
Les tests couvrent l'état non vérifié, les preuves obligatoires, les URL privées, les identifiants dupliqués et l'absence de déduction sur les pays ou paiements.
