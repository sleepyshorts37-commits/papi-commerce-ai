# PAPI IMAGE FACTORY — Fournisseurs à quota gratuit (Mission 102)

Date de recherche : 2026-11-15
Mode d'exécution visé : API intégrable aux agents, quota gratuit, aucun paiement automatique.

## Décision
PAPI IMAGE FACTORY doit accepter les fournisseurs gratuits avec limites. Le routeur peut sélectionner un fournisseur uniquement si son modèle, son quota, ses conditions d'utilisation et ses droits commerciaux sont vérifiés. Le statut gratuit ne doit jamais être supposé à partir d'une page d'accueil gratuite.

## Priorité de test

### 1. Cloudflare Workers AI — candidat principal
- Documentation officielle : https://developers.cloudflare.com/workers-ai/platform/pricing/
- Allocation annoncée sur le plan Workers Free : 10 000 Neurons par jour.
- L'offre est mesurée en Neurons, pas en nombre fixe d'images. Le nombre d'images dépend du modèle, de la résolution et des paramètres ; ne pas promettre un volume d'images précis.
- API disponible pour une intégration backend.
- Les modèles et coûts en Neurons doivent être vérifiés dans le catalogue officiel avant de choisir un modèle : https://developers.cloudflare.com/workers-ai/models/
- Le routeur doit arrêter les requêtes lorsque le quota journalier est atteint. Pas de passage au plan payant.

### 2. Pollinations.ai — fournisseur secondaire à tester
- Documentation API : https://github.com/pollinations/pollinations/blob/master/APIDOCS.md
- Accès anonyme gratuit disponible pour certains modèles gratuits, soumis à une limitation par IP.
- Documentation actuellement consultée : une image à la fois et au moins 45 secondes entre les requêtes anonymes.
- Les conditions peuvent évoluer et l'usage régulier côté serveur peut nécessiter une clé. Une clé, des crédits ou des droits payants ne sont jamais présumés gratuits.
- Avant usage commercial, vérifier les conditions du modèle exact et les droits sur les sorties.

### 3. Hugging Face Spaces ZeroGPU — option expérimentale
- Documentation officielle : https://huggingface.co/docs/hub/spaces-zerogpu
- Quota Free actuellement documenté : 5 minutes GPU par jour, avec priorité limitée.
- Ce quota concerne l'exécution GPU dans les Spaces ZeroGPU ; ce n'est pas un quota API Inference Providers.
- L'usage programmatique dépend du Space, de son API et de ses conditions. Ne pas supposer qu'un Space public autorise un service de production.
- À réserver aux essais et prototypes, sauf confirmation d'un endpoint stable et des droits.

## Règles du routeur FREE_QUOTA
1. Interroger ou lire le statut de quota du fournisseur avant toute génération lorsque l'API le permet.
2. Enregistrer le modèle exact, la date de vérification, le quota disponible et la consommation estimée/réelle.
3. Utiliser en priorité Cloudflare si le modèle choisi est disponible, dans le quota et autorisé.
4. En cas de quota épuisé ou d'indisponibilité, attendre le prochain renouvellement ou essayer un fournisseur secondaire explicitement autorisé.
5. Ne jamais activer automatiquement un abonnement, un crédit payant, un essai facturable ou un endpoint dont le prix est inconnu.
6. Plafond de dépenses configurable à zéro par défaut ; si le fournisseur ne garantit pas le mode gratuit, bloquer.
7. Les agents préparent les prompts et les tâches même si aucun quota n'est disponible ; ils ne lancent pas de requête payante.
8. Les sorties restent en statut `generated_pending_qa` jusqu'au contrôle qualité, puis `pending_human_approval`.

## Mise en service — dépendances humaines
- Le propriétaire doit créer/valider le compte Cloudflare et le compte Pollinations éventuel.
- Les tokens API ne doivent jamais être fournis dans le chat ou ajoutés au dépôt Git.
- Les secrets seront configurés dans un gestionnaire de secrets backend, après choix et autorisation explicites du propriétaire.
- Aucun déploiement ni activation de worker n'est autorisé par ce document.

## Sources
- Cloudflare Workers AI pricing : https://developers.cloudflare.com/workers-ai/platform/pricing/
- Cloudflare model catalog : https://developers.cloudflare.com/workers-ai/models/
- Pollinations API docs : https://github.com/pollinations/pollinations/blob/master/APIDOCS.md
- Pollinations terms : https://pollinations.ai/terms
- Hugging Face ZeroGPU : https://huggingface.co/docs/hub/spaces-zerogpu
