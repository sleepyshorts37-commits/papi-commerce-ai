# Mission 130 — Câblage du runtime réel Cloudflare + Supabase

## Fonction
Construit le moteur PKP-0001 à partir de secrets serveur : adaptateur Cloudflare Workers AI, registre explicite du modèle, routeur sans fallback payant, centre d'assets et ledger transactionnel partagé Supabase.

## Garde-fous
- Tous les secrets sont lus depuis l'environnement serveur uniquement.
- Construction sans requête réseau ; le premier appel fournisseur n'arrive qu'après autorisation distincte d'exécution.
- Confirmation opérateur obligatoire du forfait gratuit.
- Attestation fraîche obligatoire via le registre.
- La référence Cloudflare utilisée pour la preuve de quota doit correspondre exactement à `CLOUDFLARE_ACCOUNT_ID` dans l'environnement serveur ; toute divergence bloque la construction.
- Ledger Supabase partagé requis ; le runtime expose le ledger effectivement instancié et ne retombe pas sur le ledger mémoire.
- Plafond monétaire égal à zéro ; aucun fallback payant.

## Tests
Tests avec variables d'environnement factices et transport interdit ; vérification de l'absence d'appel réseau à la construction, du type réel de ledger partagé, de ses références de compte/worker et du rejet d'une divergence de compte.
