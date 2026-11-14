# Mission 17 — Jour 3/5

## Objectif
Améliorer la qualité du pipeline de découverte : dédoublonnage inter-sources, fraîcheur des annonces et complétude.

## Livrables
- Canonicalisation prudente des URL et empreintes SHA-256.
- Dédoublonnage déterministe avec rapport des occurrences.
- États de fraîcheur : fresh, stale, unknown, future_date.
- Contrôle de complétude des candidats.
- Tests unitaires et documentation.

## Critères d'acceptation
- Les URL identiques avec paramètres UTM différents sont reconnues comme doublons.
- Les dates sans fuseau ou invalides sont refusées.
- Les annonces anciennes, sans date ou datées dans le futur ne sont pas mises en file automatiquement.
- Aucun candidat n'est qualifié ou envoyé automatiquement.
