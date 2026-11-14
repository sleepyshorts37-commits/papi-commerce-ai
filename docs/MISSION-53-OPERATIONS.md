# Mission 53 — Consignes opérationnelles

- Utiliser uniquement des fichiers locaux déjà préparés par les outils de synchronisation.
- Vérifier la provenance des clés publiques et obtenir l'approbation propriétaire par le flux Ed25519 existant.
- Générer le manifeste après la préparation du paquet et de la charge utile.
- Conserver le manifeste comme descripteur technique, jamais comme preuve d'autorisation.
- Ne pas transmettre le manifeste ni les fichiers vers une instance distante dans cette mission.
- Ne pas considérer `delivery_id` comme un secret ou comme un mécanisme d'authentification.
- Un futur transport doit refaire les contrôles cryptographiques sur le destinataire et imposer TLS, anti-rejeu et validation humaine.
- En cas d'échec, ne pas modifier les fichiers source et ne pas tenter de contourner les contrôles.
