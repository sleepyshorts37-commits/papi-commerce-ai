# Mission 42 — Procédure opérateur

- Utiliser exclusivement des paquets synthétiques ou explicitement autorisés.
- Confirmer l'identité propriétaire, la clé publique active et la destination attendue.
- Stocker le registre SQLite sur un volume local privé avec sauvegarde contrôlée.
- Utiliser `commit_approved_sync_receipt` pour le flux atomique; ne pas appeler séparément la vérification non consommatrice puis un autre registre.
- En cas de conflit, préserver la base et examiner l'événement/la ressource. La transaction annule aussi le nonce; une nouvelle tentative doit être explicitement revue et signer un nouvel identifiant d'approbation/nonce.
- Ne pas interpréter `verified_pending_manual_import` comme une livraison ou un import.

Limites : mono-instance, fichier SQLite unique; pas de transport, import, réplication ou service distribué. Aucun worker ni scheduler n'est activé.
