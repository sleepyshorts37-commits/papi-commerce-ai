# Mission 172 — Déclenchement explicite de fabrication KDP depuis l'iPhone

## Livrable
- Service de fabrication lit un profil \`kdp-build-config.json\` privé par manuscrit, mode 0600, max 256 Kio.
- Rejette profils avec secrets/tokens, champs inconnus ou chemins contrôlés.
- Endpoint HTTPS \`POST /api/papi-kids/manuscripts/{upload_id}/build-kdp-package\`.
- Jeton distinct \`PAPI_KIDS_KDP_BUILD_TOKEN\` et drapeau serveur \`PAPI_KIDS_KDP_BUILD_ENABLED=false\` par défaut.
- Exige un corps JSON avec \`confirm: true\` et une confirmation explicite dans le tableau de bord.
- Utilise l'orchestrateur atomique broché + ebook ; retourne les chemins/manifeste, sans upload ni publication.
- Bouton iPhone ajouté, jeton effacé après succès.

## Limites opérationnelles
Le profil serveur doit être préparé avec les illustrations approuvées, le gabarit officiel KDP, les zones de texte, les polices et les paramètres d'impression. Aucun profil réel n'est installé, aucune génération réelle ni déploiement n'a été effectué.
