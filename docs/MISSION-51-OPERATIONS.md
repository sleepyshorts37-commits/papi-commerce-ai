# Mission 51 — Procédure opératoire

1. Générer une clé dans un emplacement local protégé, hors dépôt et hors sauvegardes.
2. Sauvegarder la clé séparément dans un coffre ou gestionnaire de secrets approuvé.
3. Créer le snapshot SQLite (Mission 50), puis le chiffrer avec AES-256-GCM.
4. Vérifier immédiatement le manifeste chiffré avec la clé correspondante.
5. Pour une rotation, générer une nouvelle clé, ré-encrypter vers de nouveaux fichiers et vérifier avec la nouvelle clé.
6. Conserver l'ancienne clé jusqu'à validation et selon la politique de rétention.
7. Ne jamais supprimer la seule copie déchiffrable d'une sauvegarde.

Les commandes de déchiffrement produisent une base SQLite en clair. Elles doivent être utilisées uniquement sur un volume chiffré, vers un chemin neuf et protégé. La révocation/destruction de clés reste une décision humaine explicite.