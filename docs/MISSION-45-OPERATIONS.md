# Mission 45 — Procédure opérateur

## Avant export
- Vérifier que le bundle et son approbation Ed25519 ont été créés et validés par la procédure autorisée.
- Examiner humainement les contenus proposés; les filtres automatiques ne détectent pas toutes les données personnelles.
- N'exporter que des mémoires partagées normales et des messages internes nécessaires.

## Export local
Appeler `write_sync_payload` avec le bundle approuvé, la liste explicite des enregistrements et un répertoire local privé. La fonction refuse les contenus dont le digest ne correspond pas au bundle, les identifiants non référencés, les doublons et les données exclues.

## Réception locale
Lire la charge utile avec `read_sync_payload` en fournissant le bundle exact. Cette vérification ne remplace pas la vérification Ed25519 et la consommation du nonce du récepteur Mission 44.

## Après vérification
Conserver séparément le bundle, l'approbation et le fichier .papidata. Ne pas éditer les fichiers à la main. Aucun contenu n'est écrit dans les journaux mémoire ou CHAT par cette mission. Toute intégration ultérieure nécessite une mission dédiée, une approbation propriétaire et des tests de transaction/rollback.
