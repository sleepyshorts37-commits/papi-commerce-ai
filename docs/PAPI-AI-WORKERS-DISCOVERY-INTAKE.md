# PAPI AI WORKERS — ingestion et tri des plateformes découvertes

## Mission 19 — Jour 2/5

Le module `papi_core.platform_discovery` reçoit des métadonnées de résultats provenant d'un adaptateur de recherche autorisé. Il contrôle la structure, l'identifiant, les horodatages et les URL HTTPS publiques, puis produit un état prudent et une liste de blocages.

### États et règles
- `candidate` : aucun blocage déclaré, mais toujours non vérifié et soumis à revue humaine.
- `needs_human_review` : politique IA, éligibilité Sénégal, paiement ou preuves encore incertains.
- `human_registration_required` : l'utilisateur doit créer/valider lui-même le compte.
- `rejected` : agents IA interdits, Sénégal explicitement non admissible ou paiements explicitement indisponibles.

Les valeurs `unknown` ne sont jamais interprétées comme favorables. Chaque entrée reste `verified: false`. Aucun compte n'est créé et aucune action externe n'est exécutée.

### Interface
- `review_platform_candidate(candidate)`
- `review_platform_candidates(candidates)`

Les champs de preuve sont des URL fournies par l'adaptateur ; ce module ne télécharge pas les pages et ne vérifie pas leur authenticité. Le moteur de recherche et les connecteurs réels, la persistance, la planification et les notifications sont des étapes d'intégration ultérieures.
