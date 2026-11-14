# Mission 44 — Prompt de réalisation

Relier le paquet .papisync hors ligne de la Mission 43 à la vérification Ed25519 et au reçu atomique local des Missions 40–42. Construire une façade de réception unique, sûre et fail-closed, ainsi qu'une commande CLI et des tests de bout en bout.

Contraintes impératives :
- Ne pas importer le contenu mémoire/chat ni exécuter les événements.
- Ne pas activer de transport réseau, worker, scheduler ou déploiement.
- Conserver le paquet reçu; aucune suppression ou mutation automatique.
- Vérifier propriétaire, clé publique de confiance, signature, TTL, digest, destination et portée.
- Consommer nonce + reçu + références dans la transaction atomique existante.
- Aucun secret, clé privée ou donnée client dans GitHub.
- Toute erreur doit échouer sans commit partiel.
- PR ouverte en brouillon, jamais fusionnée.
