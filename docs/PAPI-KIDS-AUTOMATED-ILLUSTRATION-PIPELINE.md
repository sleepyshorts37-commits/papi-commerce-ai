# PAPI KIDS PUBLISHING — chaîne automatisée d'illustration (Mission 118)

## Objectif produit

Depuis un iPhone, le propriétaire transmet un manuscrit à PAPI KIDS. Le système prépare et exécute la production des illustrations, sans demander à l'utilisateur de rédiger les prompts scène par scène ni de piloter les fournisseurs. Il présente ensuite les résultats pour validation humaine avant mise en page finale et publication KDP.

Cette mission raccorde le workflow éditorial PAPI KIDS au moteur PAPI IMAGE FACTORY. Elle ne déploie aucun service et ne lance aucune génération réelle.

## Parcours automatisé

1. **Réception** — créer un dossier de production et un identifiant stable pour le livre ; conserver le manuscrit original en lecture seule.
2. **Analyse éditoriale** — extraire le nombre de pages/scènes, le texte exact de chaque page, les personnages, lieux, objets et contraintes de sécurité jeunesse.
3. **Bible visuelle** — définir pour chaque personnage une fiche canonique (nom, âge fictif si pertinent, silhouette, vêtements, couleurs, signes distinctifs, expressions) et un guide de style commun.
4. **Planification** — créer une tâche par illustration avec identifiant idempotent, page, prompt, modèle autorisé, résolution cible et empreinte du prompt.
5. **Prévisualisation** — générer d'abord un petit lot de test à faible coût/quota ; faire valider la direction artistique avant le lot complet.
6. **Génération** — soumettre les lots au routeur de modèles autorisés et au moteur de production existant.
7. **Stockage** — enregistrer les octets, métadonnées, modèle, prompt hash, coût/quota et statut de chaque asset.
8. **Contrôle qualité** — vérifier l'intégrité, l'adhérence au prompt, la cohérence des personnages et du style, la composition, la lisibilité et la sécurité.
9. **Correction** — produire une nouvelle version ciblée seulement après diagnostic ; conserver les versions précédentes et leurs audits.
10. **Préparation KDP** — transmettre les assets approuvés à la mise en page, vérifier dimensions/DPI, marges, fond perdu et couverture selon les spécifications KDP applicables.
11. **Validation humaine** — présenter un aperçu complet et les fichiers finaux. Aucun PDF n'est déclaré prêt à publier tant que les contrôles requis ne sont pas passés.
12. **Publication** — étape séparée, toujours soumise à une autorisation explicite du propriétaire.

## Raccordement aux modules existants

Sur la branche de base Mission 117, les briques suivantes sont déjà présentes :

- `runtime/papi_core/image_production_engine.py` : orchestration idempotente des lots et reprise après interruption.
- `runtime/papi_core/image_asset_center.py` : stockage local des octets et métadonnées des illustrations.
- `runtime/papi_core/image_provider_cloudflare.py` : adaptateur Cloudflare Workers AI et réservation/commit/libération de quotas.
- `runtime/papi_core/image_model_router.py` : sélection des modèles explicitement autorisés et mesure du débit.
- `runtime/papi_core/image_quality_review.py` : contrôle technique et sémantique avec blocage si une vérification manque.
- `runtime/papi_core/image_quality_audit.py` : journal append-only des contrôles ; ne peut pas attribuer une approbation humaine.

Le workflow PAPI KIDS doit appeler ces composants via des interfaces injectées. Il ne doit pas créer un second moteur de génération ou contourner le registre de quotas.

## Politique de quotas et de dépenses

Le système fonctionne avec des quotas bornés, pas avec une promesse d'images illimitées.

- Quota par fournisseur, modèle, jour, livre et campagne ; réserver avant l'appel, rapprocher la consommation après l'appel.
- Limites configurables : nombre maximal d'images par livre, images par lot, concurrence, tentatives de correction et coût estimé.
- Prévisualisation basse résolution avant génération haute résolution lorsque le fournisseur le permet.
- Arrêt net lorsque le quota est épuisé, le prix inconnu, le compte non vérifié ou la réservation échoue.
- Aucun fallback vers un fournisseur payant, aucun achat de crédits, aucun abonnement et aucun dépassement silencieux.
- Plafond monétaire par défaut : **0**. Un plafond supérieur ne pourra être activé qu'après accord explicite du propriétaire et affichage du montant/devise et du coût maximal estimé.
- Le quota technique d'un fournisseur n'est pas assimilé à un droit commercial : licence, conditions d'utilisation et droits de sortie doivent être vérifiés pour le modèle exact.
- Ne jamais annoncer un nombre fixe d'images à partir d'un quota en unités (neurons, secondes GPU, tokens, crédits) sans calcul vérifié pour le modèle et les paramètres exacts.

### Configuration attendue

Les noms ci-dessous décrivent la configuration cible ; ils ne constituent pas des secrets ni des variables déjà déployées.

- `PAPI_IMAGE_DAILY_QUOTA`
- `PAPI_IMAGE_BOOK_QUOTA`
- `PAPI_IMAGE_MAX_BATCH_SIZE`
- `PAPI_IMAGE_MAX_REVISIONS_PER_PAGE`
- `PAPI_IMAGE_SPEND_CAP_MINOR=0`
- `PAPI_IMAGE_PAID_PROVIDER_ENABLED=false`
- `PAPI_IMAGE_HUMAN_APPROVAL_REQUIRED=true`

Les secrets fournisseurs doivent rester dans le gestionnaire de secrets côté serveur. Aucune clé API dans le navigateur iPhone, les prompts, les logs ou Git.

## Google / Gemini

Google Gemini est un fournisseur candidat, pas un fournisseur activé par défaut dans cette mission. Avant son activation, vérifier le modèle d'image exact, le prix courant, les limites de quota du projet Google, les droits d'utilisation commerciale, les régions et les conditions de conservation des données. L'interface gratuite Google AI Studio ne prouve pas qu'un appel API image est gratuit.

Le connecteur Google devra respecter la même interface fournisseur et le même garde-fou de quota. Si le coût est payant ou inconnu, il reste désactivé tant que le propriétaire n'a pas autorisé un plafond monétaire explicite.

## Cohérence visuelle et qualité

- Générer des références maîtresses des personnages avant les scènes ; réutiliser les mêmes descriptions et références à chaque page.
- Conserver un registre versionné des personnages et du style ; toute modification de bible visuelle doit être approuvée et tracée.
- Contrôler la continuité des vêtements, couleurs, proportions, accessoires, âge apparent et détails distinctifs.
- Ne pas faire générer le texte du livre dans l'image : le texte exact est ajouté lors de la mise en page.
- Bloquer les images présentant des anomalies, éléments inappropriés, incohérences majeures ou droits non vérifiés.
- Le score automatique ne vaut jamais validation humaine. Chaque asset final reste `pending_human_approval` jusqu'à décision explicite.

## Données et statuts par illustration

Chaque illustration conserve au minimum : `book_id`, `page_id`, numéro de page, version, prompt et hash, personnage(s) attendus, modèle/fournisseur, dimensions, type MIME, hash SHA-256, taille, quota réservé/consommé, coût estimé/réel si applicable, dates, résultat QA, motifs de blocage, statut et décision humaine.

Cycle de statut recommandé :
`planned` → `quota_reserved` → `generated` → `stored` → `qa_pending` → `pending_human_approval` → `approved` ou `rejected`.
Une erreur fournisseur ou de stockage passe en état d'incertitude à rapprocher ; pas de nouvelle génération automatique aveugle.

## Sécurité et limites de cette mission

- Aucun appel fournisseur réel pendant les tests unitaires.
- Aucun secret réel ajouté au dépôt.
- Aucun déploiement, activation de worker, achat, abonnement ou publication KDP.
- Aucun accès Google Drive ou compte Amazon supposé : les connecteurs et autorisations seront vérifiés séparément.
- Les PDF finaux doivent être contrôlés selon les exigences KDP en vigueur au moment de l'export.
- Les validations humaines restent obligatoires pour la bible visuelle, les images finales, le PDF prêt à publier et la publication.

## Critères d'acceptation

1. Un manuscrit peut être transformé en plan de scènes sans appel à un fournisseur.
2. Chaque scène reçoit un identifiant stable et une tâche reprenable.
3. Une tâche sans quota réservé est bloquée avant l'appel fournisseur.
4. Une tâche dont le prix ou les droits sont inconnus est bloquée.
5. Un lot peut reprendre sans régénérer les assets déjà stockés.
6. Chaque image stockée possède une empreinte et une trace de provenance.
7. Une image dont le contrôle qualité échoue reste bloquée.
8. Aucun contrôle automatisé ne peut positionner `human_approved=true`.
9. Le plafond de dépenses nul bloque les fournisseurs payants.
10. Aucun déploiement ni publication n'est effectué par cette mission.
