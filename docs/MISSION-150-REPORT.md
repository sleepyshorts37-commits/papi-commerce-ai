# Mission 150 — Connexion réelle du verrou FLUX au moteur de campagnes

## Livrables
- Adaptateur batch Cloudflare FLUX vers le routeur image existant.
- Propagation de l'identité livre/page/campagne et clé d'idempotence de bout en bout.
- Nouveau centre d'assets qui écrit dans le stockage privé PAPI KIDS et enregistre chaque image dans PostgreSQL.
- Reprise des enregistrements incertains sans régénération ; fichiers orphelins bloqués ; versions séparées quand le prompt change.
- Nouveau constructeur runtime PKP-0001 qui exige le registre fournisseur, la preuve de quota Workers Free, le compte serveur et le plafond dépense zéro.
- Le runtime est construit sans réseau ; la génération exige \`generation_authorized=True\`, faux par défaut.
- Le lot s'arrête au premier refus fournisseur ; aucun fallback ou upgrade.
- Tests end-to-end avec transport Cloudflare simulé, stockage privé et registre PostgreSQL simulé.

## Limites
- Aucune requête Cloudflare réelle et aucune illustration créée.
- Le quota est une attestation opérateur plus ledger PAPI, pas une lecture complète des autres usages du compte Cloudflare.
- Les sorties 1024×1024 restent réservées à l'EPUB ; le paperback attend la super-résolution et la revue humaine.
