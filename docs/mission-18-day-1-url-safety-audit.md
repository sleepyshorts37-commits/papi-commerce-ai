# Mission 18 — Jour 1 : audit et durcissement des URL

## Résultat de l'audit de Mission 17

Les signatures consommées par `global_work_pipeline.py` correspondent aux fonctions réellement exportées :
- `deduplicate_candidates` retourne `unique_candidates`, `unique_count`, `duplicate_count` et `duplicates` ;
- `assess_candidate_quality` expose `quality` avec les états `incomplete` / `needs_human_review` ;
- `evaluate_candidate_freshness` expose `freshness` ;
- `evaluate_work_opportunity` expose `status`.

Le pipeline lit bien ces clés. Cette vérification statique ne remplace pas l'exécution des tests.

## Défaut corrigé

Les validateurs précédents contrôlaient HTTPS et les identifiants, mais pouvaient accepter des URL vers localhost ou des IP privées. Ils pouvaient également laisser remonter une exception native lors de l'analyse d'un port mal formé.

Les validateurs de `global_work_quality.py` et `global_work_adapters.py` rejettent désormais :
- localhost et les suffixes locaux `.localhost`, `.local`, `.internal` ;
- les adresses IP qui ne sont pas globalement routables ;
- les ports mal formés et les ports autres que 443 ;
- les identifiants intégrés à l'URL et les schémas non HTTPS.

Des tests de régression couvrent IPv4 privée, loopback IPv4, loopback IPv6, hôte local et port mal formé.

## Limites

Ces contrôles valident une URL de référence ; ils ne prouvent ni l'existence du site, ni la fiabilité de l'offre, ni son admissibilité au Sénégal. Aucun accès réseau, DNS, scraping, redirection, candidature ou paiement n'est effectué. Les payloads restent fournis par une source externe autorisée.

## État CI

La PR #146 et la PR #147 n'avaient pas de résultats visibles pour les tests principaux au moment de l'audit ; seul le contrôle Supabase Preview apparaissait en état `skipped`. Les PR #144 et #145 avaient leurs contrôles principaux en succès. Les nouveaux tests de cette branche doivent encore être exécutés par GitHub Actions avant toute affirmation de validation.
