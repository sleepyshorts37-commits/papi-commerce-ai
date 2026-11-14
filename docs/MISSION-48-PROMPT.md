# Mission 48 — Unifier progressivement les écritures mémoire et PAPI CHAT

## Objectif
Introduire un magasin SQLite local append-only comme option d'écriture et de lecture pour les journaux mémoire et PAPI CHAT, sans casser la compatibilité JSONL et sans activer de synchronisation réseau.

## Travaux
1. Créer un adaptateur SQLite local partagé avec contraintes d'identité, transaction et append-only.
2. Permettre à la mémoire d'écrire/lire en SQLite, y compris les événements d'archivage.
3. Permettre à PAPI CHAT d'écrire/lire en SQLite.
4. Préserver le comportement JSONL par défaut et les lecteurs d'import de la Mission 47.
5. Tester les collisions, permissions, liens symboliques, append-only, compatibilité et isolation des données.
6. Documenter une migration manuelle progressive et ses limites.

## Garde-fous
Aucun déploiement, migration distante, worker, scheduler, transport réseau, publication, contact client ou action financière. Aucun secret ni contenu client ne doit être ajouté au dépôt.
