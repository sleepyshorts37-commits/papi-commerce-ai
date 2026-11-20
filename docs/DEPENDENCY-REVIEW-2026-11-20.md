# Revue des dépendances open source — 20 novembre 2026

## Inventaire observé

Le seul paquet runtime direct déclaré dans requirements.txt est cryptography. Le dépôt ne contient pas de fichier de verrouillage complet des dépendances ni de fichier LICENSE à la racine. Aucun code tiers n'a été copié dans cette modification.

## Correction de sécurité

La contrainte précédente cryptography>=42.0,<47.0 autorisait des versions concernées par plusieurs avis de sécurité publiés en 2026 :
- GHSA-jwv3-5hgf-82ww / CVE-2026-69249 : traitement coûteux de chaînes de certificats avec doublons, corrigé à partir de 49.0.0 ;
- GHSA-537c-gmf6-5ccf / CVE-2026-34180 : OpenSSL embarqué vulnérable dans les wheels, corrigé en 48.0.1 ;
- GHSA-p423-j2cm-9vmq / CVE-2026-39892 : dépassement de tampon via des vues mémoire non contiguës, corrigé en 46.0.7.

La contrainte est désormais cryptography==50.0.2. PyPI indique pour cette version une licence Apache-2.0 OR BSD-3-Clause, un état Production/Stable et une publication le 30 septembre 2026. Les avis cités ne couvrent pas cette version selon les plages de versions publiées. Une nouvelle analyse doit être exécutée à chaque mise à jour ; ce constat n'est pas une garantie d'absence de vulnérabilité future.

## Licence et maintenance

cryptography est maintenu par le projet Python Cryptographic Authority. Sa double licence permet l'utilisation sous Apache-2.0 ou BSD-3-Clause selon les conditions correspondantes. Les notices et obligations de la distribution choisie doivent être conservées.

Le dépôt PAPI lui-même ne déclare pas encore de licence. Aucune licence de projet n'est ajoutée automatiquement : le propriétaire doit choisir explicitement les droits de réutilisation et de redistribution.

## Dépendances transitives et compatibilité

Le dépôt ne contient pas de lockfile transplateforme. Sur le runner Ubuntu 26.04 / Python 3.14, l'installation de cryptography 50.0.2 a résolu cffi 2.1.1 puis pycparser 3.12. Ces versions transitives ne sont pas encore verrouillées ; elles sont incluses dans l'audit du graphe résolu.

Le premier run a aussi révélé un conflit avec le pyOpenSSL préinstallé globalement sur l'image du runner (pyOpenSSL 25.3.0 exige cryptography<47). Le workflow installe désormais le runtime dans un environnement virtuel isolé et exécute pip check avant les tests, afin de ne pas hériter des paquets système préinstallés. pip-audit est lui-même isolé dans un second environnement temporaire.

Avant une production multi-plateforme, produire un lockfile reproductible par cible (versions et hashes), puis tester Linux, Windows et les versions Python réellement supportées.

## Risque d'exploitation et verrouillage

- cryptography fournit des primitives cryptographiques natives ; garder la version dans une plage corrigée et surveiller les avis upstream.
- Les wheels peuvent embarquer OpenSSL ; la provenance et la version du paquet doivent être contrôlées, pas seulement la bibliothèque OpenSSL du système.
- Ne pas dépendre d'une API propriétaire pour l'ancrage : le code expose un contrat AnchorStore fournisseur-neutre.
- Les adaptateurs externes futurs devront documenter licence, quotas, export des données, rétention, suppression, disponibilité, coût et possibilité de migration.
- Aucun fournisseur payant ou service distant n'est sélectionné.

## Vérification CI

Le workflow exécute pip-audit --strict -r requirements.txt dans un environnement temporaire séparé. Il vérifie les dépendances directes et transitives résolues au moment du run. Le résultat doit être consulté sur le SHA exact de la PR ; un résultat futur peut changer si l'index de vulnérabilités est actualisé.
