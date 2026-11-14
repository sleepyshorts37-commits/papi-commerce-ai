# Mission 39 — Notes opérateur

## Fonction disponible
Le module `papi_core.sync_bundle` construit et valide une enveloppe référentielle locale. Il contrôle la version, la destination attendue, les identifiants, les empreintes SHA-256, les curseurs contigus et l'absence de doublons.

## Limites impératives
- Les événements ne contiennent que des références et empreintes; aucun corps de message ni contenu mémoire.
- Le digest prouve l'intégrité accidentelle du paquet, pas l'identité cryptographique de son émetteur.
- Le validateur ne vérifie aucune signature ni approbation propriétaire.
- Aucun import, écriture, transport réseau ou accès Supabase n'existe dans ce module.

## Avant toute exploitation future
Ajouter signature Ed25519 liée au digest et à la destination, consommation atomique du nonce dans un stockage partagé, prévalidation transactionnelle, déduplication persistante et tests d'intégration sur deux instances synthétiques. Exiger revue de sécurité et autorisation explicite du propriétaire.