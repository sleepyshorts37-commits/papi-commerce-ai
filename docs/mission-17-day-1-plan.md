# Mission 17 — PAPI GLOBAL WORK — plan de cinq jours

## Objectif global
Construire une chaîne de découverte et qualification des missions rémunérées, respectueuse des conditions d'accès, de l'éligibilité depuis le Sénégal et des autorisations du propriétaire.

## Jour 1 — Contrat de sources et ingestion (livré)
- Registre des sources avec type, statut, politique d'accès et conditions.
- Validation fail-closed des sources.
- Normalisation de lots déjà collectés, provenance et dédoublonnage.
- Tests unitaires et documentation.

## Jour 2 — Adaptateurs de lecture autorisés
- Définir des adaptateurs sans navigateur ni scraping non autorisé.
- Prendre en charge uniquement les API publiques/documentées ou flux explicitement autorisés.
- Aucun secret ni authentification de compte personnel dans le dépôt.

## Jour 3 — Qualité et cycle de vie
- Détection des doublons inter-lots, dates de publication/expiration et données périmées.
- Traçabilité des rejets et mise à jour contrôlée des opportunités.

## Jour 4 — Qualification économique et Sénégal
- Vérifier pays admissibles, moyens de paiement, frais, coûts, temps et rentabilité.
- Séparer les faits confirmés des informations inconnues.
- Exclure les tâches nécessitant usurpation, présence humaine simulée ou réponses personnelles fabriquées.

## Jour 5 — Contrôle final
- Tests intégrés et scénarios négatifs.
- Documentation, rapport et roadmap.
- Ouvrir une PR et vérifier la CI sur le SHA exact.
- Ne pas fusionner ni déployer sans autorisation.

## Critères d'acceptation
- Source non autorisée ou non vérifiée refusée par défaut.
- Provenance attachée à chaque opportunité acceptée.
- Dédoublonnage déterministe.
- Aucun appel réseau, candidature, message, paiement ou publication automatique dans cette mission sans autorisation séparée.
