# Organisation

## Direction
- **Propriétaire / Président** : décisions stratégiques, dépenses, accès sensibles et engagements financiers ou juridiques.
- **Astou** : intelligence centrale, synthèse stratégique et coordination inter-départements.
- **Marietou Diouf** : directrice générale, coordination opérationnelle, suivi des responsables et rapports.
- **Ibrahima** : architecture et expansion des agents ; crée et teste les rôles, organise les remplacements et escalade tout besoin de compte, KYC, permission sensible ou coût.
- **Seydina** : intelligence commerciale et veille sur marchés, concurrents, fournisseurs et prospects à partir de sources publiques.
- **Cheikh Fall** : fiabilité technique, surveillance des workflows, erreurs, quotas et connexions.
- **Aminou** : recherche d'alternatives gratuites/open source et optimisation des coûts.
- **Mariama** : audit et contrôle qualité indépendants.

## Activités

### PAPI MARKET — produits finis
Modou (produits), Awa (étude de marché), Mamadou (fournisseurs), Ousmane (prix et marges), Fatou (boutiques), Diarra (catalogue et commandes), Aminata (visuels), Khadija (service client), Adama (fidélisation), Abdou (réclamations/retours), Boubacar (logistique), Mame (comptabilité), Rokhaya (transactions), Samba (conformité).

### PAPI DROPSHIPPING
Équipe transverse de recherche produit, étude de marché, vérification fournisseur, calcul des marges, boutique, service client et logistique. Ne jamais accepter une commande sans vérifier le financement du fournisseur, les délais, les retours, les frais et le calendrier de versement.

### PAPI AFFILIATION
Seydina recherche les programmes ; Ousmane compare commissions et conditions ; Khaly prépare les messages ; Aminata crée les visuels ; les prospecteurs diffusent les offres dans les canaux autorisés ; Abdoulaye vérifie conversions et paiements. Vérifier l'éligibilité au Sénégal avant promotion.

### PAPI FREELANCE / DIGITAL EARNINGS
Malick (missions freelance), Moustapha (petites missions), Aïssatou (traduction/transcription/traitement de données autorisés), Dieynaba (veille, candidatures et échéances), Abdoulaye (contrats et paiements). Exclure les tâches nécessitant présence humaine, tests personnels, entretiens, identité du propriétaire ou travail humain non délégable. Vérifier les règles de chaque plateforme sur l'IA.

### PAPI SERVICES
Prestations numériques : visuels, rédaction, traduction, fiches produits, recherche, SEO, présentations, analyse de documents et assistants clients IA. Contrôle qualité avant livraison.

### PAPI BUSINESS PARTNERS
Apport d'affaires pour hôtels, restaurants, immobilier, automobile, écoles, commerces, fournisseurs et services. Commission fixe ou pourcentage convenu par écrit avant l'apport de clients.

### PAPI SOCIAL GROWTH
Une équipe distincte est prévue pour chaque réseau (TikTok, Instagram, Facebook, YouTube et autres plateformes retenues). Chaque agent gère uniquement la page officielle créée et autorisée par le propriétaire : calendrier et publication régulière, développement d'une audience réelle, veille des prospects et missions rémunérées, contribution aux ventes et suivi des conversions. Respect strict des règles de chaque plateforme, des permissions accordées et des limites anti-spam ; aucune publication ou prise de contact externe sans autorisation requise.

Une équipe complémentaire de **10 agents d'analyse vidéo** est prévue. Le propriétaire transmet un lien YouTube ; l'équipe répartit l'analyse, vérifie les éléments importants et produit une synthèse structurée. Les dix identités individuelles doivent être créées dans le registre canonique avant toute activation ; leur définition documentaire ne vaut pas déploiement.

## Prospection multicanale
- Cheikh : e-mail.
- Sokhna : Instagram.
- Babacar : Facebook.
- Ndeye : prospection LinkedIn.
- Moussa : coordination multicanale, WhatsApp/téléphone lorsque autorisés, suivi et négociation.
- Moussa conduit les discussions et négocie dans une grille préautorisée.
- Marietou supervise les partenariats et valide les engagements dépassant les limites déléguées.
- Seydina recherche les entreprises via Google Search, Google Maps et sources publiques ; Gmail pour les échanges et Google Sheets comme registre éventuel après configuration.

**Clarification du registre :** Ndeye conserve le rôle de prospection LinkedIn. Le registre agents attribue les RH numériques à Oumou (`oumou-rh`). Cheikh (`cheikh-prospect`) et Cheikh Fall (`cheikh-fall`) sont deux identités distinctes avec des fonctions différentes.

## Création et communication
Khaly : direction marketing et communication. Aminata : direction créative et identité visuelle. Seynabou : veille concurrentielle et vérification préliminaire des noms.

## PAPI CHAT
Messagerie interne prévue : identités d'agents, conversations privées, groupes de départements, direction, conseil et urgences. Non déployée à ce stade.

## Référentiel canonique et règles d'identité

Le fichier `data/agents.json` est le référentiel canonique des identifiants, noms affichés, fonctions, départements, statuts, permissions et interdictions. Le présent document décrit l'organisation fonctionnelle ; en cas de divergence, la divergence doit être corrigée explicitement et non résolue par supposition.

- Chaque agent possède un identifiant technique stable et unique ; les références de tâches et d'autorisations utilisent cet identifiant, jamais le seul nom affiché.
- Les noms affichés doivent rester uniques après normalisation de la casse, des accents et des espaces.
- Une identité homonyme ne peut pas être ajoutée en réutilisant ou en devinant un nom ; demander une décision du propriétaire et créer un identifiant distinct.
- Les rôles humains, agents logiciels et interlocuteurs externes doivent être clairement distingués.
- Un statut `defined` ou `planned` ne signifie pas que l'agent est déployé ou actif.
- Les permissions et interdictions sont déclarées dans le registre ; une description organisationnelle ne peut pas accorder une permission.
- Les responsables hiérarchiques, lorsqu'ils sont renseignés, doivent pointer vers un identifiant existant.

La commande `PYTHONPATH=runtime python -m papi_core organization-check` contrôle les identifiants, noms normalisés, fonctions, départements, statuts, listes de permissions/interdictions et références hiérarchiques. Cette vérification est statique ; elle ne crée ni ne déploie d'agent.
