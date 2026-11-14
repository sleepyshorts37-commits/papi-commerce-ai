# Mission 42 — Prompt détaillé

Éliminer la fenêtre de panne entre la consommation du nonce Ed25519 et l'inscription du reçu de synchronisation. Ajouter un mode de vérification cryptographique sans consommation anticipée du nonce, puis consommer le nonce et enregistrer le reçu ainsi que toutes ses références dans une seule transaction SQLite.

Exigences : vérification stricte de la signature, du propriétaire, de la clé active, du scope, du TTL, du digest et de la destination; anti-rejeu unique dans la transaction; idempotence d'un paquet déjà reçu avec une nouvelle approbation valide; rollback du nonce et du reçu en cas de conflit; tests adversariaux; documentation et roadmap.

Aucune importation de contenu, aucun transport, déploiement, worker, scheduler, migration distante, contact externe, publication, paiement ou dépense. PR ouverte, brouillon et non fusionnée; CI validée sur le SHA final exact.
