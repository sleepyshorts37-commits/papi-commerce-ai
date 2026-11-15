# Mission 111 — PAPI IMAGE FACTORY Production Planner

## Objectif prioritaire
Rapprocher PAPI de la production rapide d'illustrations : préparer les pages, répartir les tâches en lots adaptés aux quotas, les exécuter explicitement via l'adaptateur parallèle de la mission 110, puis produire un manifeste vérifiable.

## Correctif SQL découvert pendant la vérification
Le workflow quota a ensuite dépassé les tests Python et échoué dans la RPC de réservation : les noms de sortie `quota_day` et `reserved_units` de la fonction PL/pgSQL entraient en collision avec des références SQL non qualifiées. Les références aux colonnes de la table de quotas ont été qualifiées avec des alias. Cette correction est incluse dans la PR 111 et attend une nouvelle exécution PostgreSQL.

## Livrables
- `runtime/papi_core/image_factory.py`
  - planification déterministe par livre ;
  - validation des prompts, identifiants, numéros et priorités ;
  - tri par priorité puis numéro de page ;
  - clés d'idempotence stables ;
  - lots limités en nombre d'images et en unités estimées ;
  - exécution explicite d'un lot par `generate_many` ;
  - manifeste de métadonnées avec SHA-256, taille, MIME, statut de revue humaine.
- `tests/test_image_factory.py`
  - déterminisme et bornes de lots ;
  - priorités ;
  - idempotence ;
  - refus des modèles inconnus et des pages dupliquées ;
  - manifeste et erreurs.
- `docs/PAPI-IMAGE-FACTORY-PRODUCTION-PLANNER.md`
  - usage, limites, sécurité et exemple de découpage.

## Garanties
- La planification est hors ligne et ne consomme aucun quota.
- Aucun retry automatique.
- Chaque génération passe par l'adaptateur de la mission 110 et son registre partagé.
- Les images générées restent en attente de revue visuelle ; aucune approbation automatique.
- Les octets ne sont pas enregistrés dans le manifeste JSON.
- Aucun stockage cloud, worker permanent ou fournisseur payant n'est activé.

## Validation
Les tests unitaires ont été ajoutés mais attendent une exécution CI sur la PR. Le workflow quota précédent a révélé le conflit PL/pgSQL décrit ci-dessus ; le correctif de qualification SQL est inclus mais non encore validé. Aucun appel réel Cloudflare ou Supabase Storage n'a été effectué. Les estimations d'unités doivent être mesurées par modèle et confirmées pour le compte avant utilisation en production.

## Limites et suite
Le manifeste est prêt, mais le stockage durable, le contrôleur de qualité visuelle automatisé, la continuité des personnages, l'assemblage PDF et le pilotage d'une file multi-livres restent à implémenter. La mission suivante doit relier ce planificateur au stockage d'assets et au contrôle qualité sans activer de worker permanent.
