# Mission 178 — Autorisation finale explicite du propriétaire

## Livrable
- Migration PostgreSQL 022 : journal append-only des autorisations finales, identité propriétaire, version et hash du manifeste, phrase exacte, date, notes et référence de preuve.
- Endpoint HTTPS POST séparé, jeton propriétaire dédié et identifiant propriétaire configuré côté serveur.
- La confirmation est refusée si un PDF/EPUB n'a pas sa revue hash-bound, si Kindle Previewer manque pour un ebook, si la sécurité jeunesse est refusée, si les droits/métadonnées sont incomplets ou si le plafond n'est pas zéro.
- Le tableau de bord iPhone propose la confirmation finale avec phrase exacte et avertissement de soumission manuelle.
- Le statut du livre expose l'autorisation enregistrée.

## Gouvernance
L'autorisation porte uniquement sur une soumission manuelle. Aucun endpoint de téléversement KDP, aucun clic Amazon, aucune publication automatique, aucun appel fournisseur et aucune dépense.
