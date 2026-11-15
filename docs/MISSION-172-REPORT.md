# Mission 172 — Service de fabrication KDP à déclenchement explicite

## Livrable
- Service lit un profil JSON privé \`kdp-build-config.json\` dans le dossier du manuscrit.
- Profil limité à 256 Kio, fichier non symbolique, permissions 0600.
- Rejette propriétés inconnues, secrets, tokens, chemins d'exécution et identifiants contrôlés.
- Exécute l'orchestrateur atomique broché + ebook uniquement après appel explicite du service.
- Retourne le manifeste et les chemins privés ; n'autorise jamais l'upload ou la publication.
- Tests offline sur profil absent, permissions, secrets, propriétés inconnues et invocation.

## Mise en service
Le profil doit être créé côté serveur par un opérateur ou un processus de mise en page approuvé. Il contient uniquement les arguments de fabrication (positions, images approuvées, gabarit KDP, police, paramètres de coupe). Aucun profil ni secret n'est envoyé depuis le navigateur.
