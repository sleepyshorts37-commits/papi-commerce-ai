# Mission 53 — Prompt de réalisation

Concevoir un contrat de préparation de transfert inter-instances pour PAPI COMMERCE AI, en reliant de façon déterministe le paquet `.papisync` signé et la charge utile `.papidata`.

Contraintes obligatoires :
- Aucun réseau, endpoint distant, hébergement, déploiement ou service tiers.
- Aucune consommation de nonce, réception, import, fusion ou exécution.
- Vérifier les fichiers locaux, leur canonicalisation, leurs digests, tailles et cohérence source/destination.
- Refuser les liens symboliques, fichiers non réguliers, structures inattendues, clés JSON dupliquées et contenus non canoniques.
- Produire un identifiant de livraison déterministe couvrant les métadonnées et les garde-fous.
- Conserver l'approbation Ed25519 comme autorité ; le manifeste n'est pas une signature.
- Ajouter tests de réussite, falsification, destination incohérente, lien symbolique et drapeaux d'exécution.
- Documenter les garanties et limites, mettre à jour la roadmap, vérifier CI sur le SHA final.
- La PR reste ouverte en brouillon et non fusionnée.
