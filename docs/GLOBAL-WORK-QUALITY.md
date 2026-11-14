# PAPI GLOBAL WORK — qualité et fraîcheur des opportunités

## Jour 3/5

Le module `papi_core.global_work_quality` fournit quatre contrôles déterministes :

- Canonicalisation d'URL HTTPS et retrait des paramètres de suivi usuels.
- Empreinte stable et détection des doublons entre flux.
- Fraîcheur basée sur une date ISO-8601 avec fuseau horaire.
- Contrôle de complétude des champs, sans inventer les informations absentes.

## Règles de sécurité

- Une date absente ou invalide n'est jamais considérée comme fraîche.
- Une date future est mise à l'écart.
- Les offres dépassant la fenêtre de fraîcheur sont marquées périmées.
- Un candidat incomplet reste non qualifié et nécessite une revue humaine.
- Le module ne soumet aucune candidature et ne contacte aucune plateforme.
- La canonicalisation ne suit jamais de redirection et n'effectue aucun accès réseau.

La déduplication conserve la première occurrence dans l'ordre d'entrée et signale les doublons avec leur index d'origine.
