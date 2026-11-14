# Mission 41 — Procédure opérateur

- Utiliser un paquet validé et une destination exacte.
- Vérifier l'identité propriétaire et son attestation Ed25519 fraîche.
- Employer un nonce neuf pour chaque tentative.
- Stocker SQLite dans un répertoire privé et sauvegardé.
- Examiner tout conflit d'événement/ressource; ne jamais supprimer un reçu pour contourner un conflit.

Un reçu « verified_pending_manual_import » signifie uniquement que le paquet a été authentifié et ses références enregistrées localement. Il ne signifie ni import, ni livraison, ni convergence, ni activation d'un worker.

En cas d'erreur, préserver la base et demander une revue propriétaire. Une nouvelle tentative exige une nouvelle enveloppe signée et un nonce inédit.

Limites : registre mono-instance; pas d'atomicité entre consommation du nonce et écriture du reçu; aucun stockage distribué, transport ou import réel.
