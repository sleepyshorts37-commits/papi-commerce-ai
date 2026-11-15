# Mission 130 — Câblage du runtime réel Cloudflare + Supabase

## Fonction
Construit le moteur PKP-0001 à partir de secrets serveur : adaptateur Cloudflare Workers AI, registre explicite du modèle, routeur sans fallback payant, centre d'assets et ledger transactionnel partagé Supabase.

## Garde-fous
- Tous les secrets sont lus depuis l'environnement serveur uniquement.
- Construction sans requête réseau ; le premier appel fournisseur n'arrive qu'après autorisation distincte d'exécution.
- Confirmation opérateur obligatoire du forfait gratuit.
- Attestation fraîche obligatoire via le registre.
- Ledger Supabase partagé requis ; pas de ledger mémoire comme autorité multi-worker.
- Plafond monétaire égal à zéro ; aucun fallback payant.

## Tests
Tests avec variables d'environnement factices et transport interdit ; vérification qu'aucune requête réseau n'est faite à la construction.
