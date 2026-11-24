# Mission 196 — Archives vérifiables du journal d'audit

## Objectif
Préparer un snapshot complet et restaurable du journal d'audit, lié à un checkpoint d'ancrage vérifié, sans rotation ni suppression automatique de la source.

## Changements
- Ajoute `runtime/papi_core/audit_archive.py` avec création, vérification et restauration d'archives locales.
- Le manifeste canonique contient la taille et le SHA-256 exacts du JSONL, le nombre d'événements, les hashes de début/fin et l'identité/digest/séquence du checkpoint.
- La création exige un checkpoint courant correspondant exactement à la tête du journal.
- La vérification contrôle les octets, le manifeste, la chaîne JSONL complète et l'appartenance du checkpoint à la chaîne d'ancrage vérifiée.
- La restauration refuse les chemins existants, crée un fichier privé 0600 et relit le résultat.
- Les répertoires et fichiers d'archive sont privés (0700/0600) ; les liens symboliques et les chemins parents symboliques sont refusés.
- La source n'est jamais tronquée, supprimée ou remplacée.
- Ajoute neuf tests de régression et documente le format et les limites.

## Validation
- Tests locaux : non exécutés dans cette session.
- CI GitHub Actions : déclenchée par la PR ; les résultats doivent être confirmés sur le SHA final.
- Les tests utilisent un adaptateur d'ancrage mémoire exclusivement en test. Aucun fournisseur réel ou stockage distant n'est configuré.

## Limites
- Il s'agit d'un snapshot complet, pas d'une rotation ni d'un archivage segmenté.
- Aucun chiffrement applicatif, transfert hors site, rétention WORM ou purge n'est implémenté.
- Les archives contiennent le journal complet et ne doivent jamais être ajoutées au dépôt public.
- Aucune CLI n'est exposée, car aucun adaptateur de stockage d'ancrage opérationnel n'existe.
- Une revue indépendante et un stockage externe autorisé restent nécessaires avant exploitation.

## État de la PR
- PR brouillon empilée sur Mission 195 (#372), ouverte et non fusionnée.
- Branche : `mission-196-verified-audit-archives`.
- Base : SHA `7528e9cae599ea5bd2aeb68ddbea3b7c9c3c9e15`.
- Aucun changement sur `main`.

## Gouvernance
Aucun agent ou worker activé, aucun scheduler permanent, aucun compte externe, secret, paiement, fournisseur payant, transfert réseau ou déploiement. Aucun contact externe ni action commerciale réelle.
