# Mission 72 — Vérification de provenance Ed25519 des artefacts

## Objectif
Ajouter une vérification détachée de provenance cryptographique des rapports/artefacts, liée aux octets exacts et à une version de clé publique du registre de confiance.

## Périmètre
- Vérification uniquement : aucun chargement, création, modification ou usage de clé privée.
- Réutilisation du registre public Ed25519 versionné existant.
- Vérification des clés courantes et historiques, y compris après révocation, à des fins d'audit uniquement.
- Aucune autorisation d'action, consommation de nonce, écriture de registre ou accès réseau.

## Journées de travail
1. Auditer les primitives Ed25519 et le registre public versionné existants ; fixer le format strict de preuve.
2. Implémenter la vérification de signature détachée sur les octets exacts, avec digest SHA-256 et limite de taille.
3. Ajouter les tests de vecteur public RFC 8032, d'altération, de clé/version inconnue et d'identité révoquée.
4. Documenter la séparation entre provenance, intégrité, authentification temps réel et autorisation.
5. Exécuter les tests ciblés et la CI sur le SHA final ; ouvrir une PR brouillon dépendante de Mission 71.

## Format de preuve v1
Objet exact : `schema_version`, `algorithm`, `agent_id`, `key_version`, `artifact_sha256`, `signature`.
La signature Ed25519 porte sur les octets exacts de l'artefact ; le digest SHA-256 déclaré doit correspondre à ces mêmes octets. Les octets doivent être fournis par l'appelant et leur provenance de stockage reste hors périmètre.

## Critères d'acceptation
- Refus des champs inconnus, algorithmes/version/digest/signatures mal formés.
- Vérification avec une clé publique unique correspondant à l'identité et à la version.
- Vérification historique possible sans restaurer d'autorisation.
- Retour explicite `authorization_granted=False` et `nonce_consumed=False`.
- Aucun secret ou clé privée dans les fixtures, tests, journaux ou commits.

## Limites
Une signature valide établit que la clé privée correspondant à la clé publique du registre a signé les octets. Elle ne prouve pas à elle seule que le contenu est vrai, que l'agent avait droit à une action, ni que le registre public lui-même est authentique. La confiance dans le registre et l'approbation humaine restent nécessaires.
