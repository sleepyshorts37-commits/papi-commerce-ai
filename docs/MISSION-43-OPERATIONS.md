# Mission 43 — Procédure opérateur

1. Créer un dossier spool local privé, distinct des dépôts Git.
2. Générer le paquet avec une approbation Ed25519 signée et valide.
3. Appeler write_sync_package pour créer le fichier .papisync.
4. Copier manuellement le fichier vers le destinataire via un canal autorisé.
5. À destination, appeler read_sync_package pour vérifier structure et empreintes.
6. Vérifier ensuite la signature Ed25519 et la destination attendue avec le mécanisme d'approbation; ne jamais assimiler la lecture à une authentification.
7. Utiliser le registre atomique de Mission 42 avant toute étape d'import ultérieure, qui demeure désactivée dans cette mission.

Ne jamais inclure de clé privée, secret ou contenu client dans le fichier. Ne pas activer de transport réseau, d'agent ou de traitement automatique. En cas de doute, mettre le fichier en quarantaine sans l'exécuter ni l'importer.
