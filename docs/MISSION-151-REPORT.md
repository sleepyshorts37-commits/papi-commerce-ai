# Mission 151 — Revue éditoriale humaine sur iPhone

## Livrables
- Aperçu authentifié des 24 prompts, de la bible graphique et du storyboard PKP-0001.
- L'aperçu compare le SHA-256 du manuscrit privé reçu avec la V2 canonique ; une autre version ne peut pas être approuvée.
- Approbation possible uniquement après analyse structurelle \`analysis_ready\`, avec 24 prompts valides.
- Approbation enregistrée dans PostgreSQL et dans les métadonnées privées : upload ID, SHA du bundle source, SHA du manuscrit, réviseur et date.
- Le tableau de bord iPhone permet de consulter les prompts, la bible et le storyboard, puis d'approuver explicitement.
- Le jeton de revue est distinct du jeton de dépôt et n'est pas conservé dans l'interface.
- Le runtime de génération exige désormais l'approbation persistée liée au bon upload et au SHA exact des sources, en plus de l'autorisation distincte de génération et du plafond zéro.
- Les ressources éditoriales PKP-0001 sont intégrées à l'image Docker ; l'utilisation des ressources embarquées est activée explicitement.

## Séparation des décisions
1. Dépôt du manuscrit.
2. Analyse structurelle locale.
3. Consultation et approbation humaine du plan éditorial.
4. Autorisation distincte de génération d'images avec quota gratuit confirmé.
5. Revue humaine des illustrations.
6. Validation de la maquette KDP et autorisation de publication.

L'approbation éditoriale ne lance aucune génération d'image, aucun appel fournisseur et aucune dépense.
