# Mémoire partagée des agents PAPI

## Rôle
La mémoire conserve les faits, décisions, projets, résultats, procédures et leçons durables. Elle est distincte de PAPI CHAT : le chat transporte des messages ; la mémoire conserve des éléments réutilisables et sourcés.

## API locale
- `remember_fact(...)` ajoute une entrée.
- `search_memory(...)` recherche les entrées accessibles.
- `supersede_memory(...)` archive logiquement une entrée sans effacer son historique.

Chaque événement conserve un identifiant, une date UTC, l'acteur, la catégorie, le titre, le contenu, la source, la confiance, la portée, les tags et la sensibilité. Le journal JSONL est append-only et créé avec des permissions restrictives (`0600`).

## Portées et autorité
- `shared` : visible par tous les agents et le propriétaire.
- `agent` : visible par l'auteur et le propriétaire.
- `owner` : visible uniquement par le propriétaire.
- Seul `owner` peut enregistrer ou archiver une décision officielle.
- Les entrées de sensibilité `restricted` sont refusées. Ne pas stocker de données personnelles, secrets, identifiants, coordonnées, tokens, OTP, PIN ou CVV.

## Limites
- Stockage local sur un seul processus écrivain ; pas de synchronisation multi-machine ni de base distante.
- Les fonctions ne prouvent pas l'identité réelle de l'acteur : l'intégration au runtime devra authentifier les agents avant d'accepter leurs identifiants.
- Pas d'IA, de recherche sémantique, de scheduler ou d'accès externe.
- Ne pas committer le journal réel dans le dépôt public. Le chemin par défaut est `data/memory/events.jsonl`, qui doit rester local et ignoré par Git.

## Tests
Depuis la racine : `PYTHONPATH=runtime python -m unittest discover -s tests -v`.

## Statut
Socle logiciel local ajouté ; mémoire non déployée et non alimentée automatiquement par les agents.
