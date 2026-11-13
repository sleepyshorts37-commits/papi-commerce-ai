# Canaux de communication du propriétaire — voix et e-mail

## Objectif

Permettre au propriétaire de dialoguer oralement avec les IA responsables et permettre à ces responsables de lui adresser des e-mails proactifs, y compris en dehors des heures habituelles. Cette spécification définit les contrats et les garde-fous ; elle n'active aucun fournisseur externe.

## État de livraison

- Spécification Phase 2B, jour 1 : documentée.
- Fournisseur de reconnaissance vocale (STT) : non choisi, non connecté.
- Fournisseur de synthèse vocale (TTS) : non choisi, non connecté.
- Fournisseur e-mail : non choisi, non connecté.
- Adresse du propriétaire / liste d'autorisation : non configurée.
- Envoi externe, écoute permanente, microphone en arrière-plan et agents autonomes : désactivés.

## Architecture cible

Le canal de communication est séparé du moteur de décision des agents :

1. Le moteur produit un message structuré (agent, rôle, motif, priorité, contenu).
2. Le routeur de communication vérifie l'identité de l'agent, ses permissions, la destination et la politique.
3. Le canal choisi transforme le contenu en texte, audio ou e-mail.
4. Le journal d'audit enregistre l'intention, le résultat, l'identifiant de corrélation et les métadonnées nécessaires, sans enregistrer les secrets.
5. Toute erreur du fournisseur ferme l'envoi et crée un incident consultable ; aucun basculement vers un autre compte ou destinataire n'est implicite.

Les interfaces STT, TTS et e-mail doivent être des adaptateurs injectés. Aucun secret de fournisseur ne doit être stocké dans Git, dans le registre des agents, dans les prompts ou dans les journaux.

## Conversation vocale

### Flux entrant
- Le propriétaire déclenche explicitement une session audio depuis l'interface.
- Le flux audio est transcrit en texte par un adaptateur STT.
- Le texte transcrit est présenté à l'agent chef sélectionné avec l'identité de session et un identifiant de corrélation.
- Les commandes sensibles exigent une confirmation textuelle ou une validation explicite dans l'interface ; une transcription seule ne vaut pas signature cryptographique ni approbation financière.

### Flux sortant
- L'agent répond en texte, puis un adaptateur TTS produit la voix.
- Chaque chef possède un identifiant de profil vocal stable et distinct ; les profils utilisent des voix synthétiques autorisées, pas l'imitation non consentie d'une personne réelle.
- La voix ne confère aucune permission supplémentaire : les mêmes règles d'autorisation s'appliquent au texte et à l'audio.

### Confidentialité
- Pas d'écoute continue ni d'activation du microphone en arrière-plan par défaut.
- Pas de conservation des fichiers audio bruts par défaut.
- La conservation des transcriptions doit être configurable et limitée au besoin opérationnel.
- Indiquer clairement lorsqu'une réponse est synthétisée par IA.

## E-mail proactif des IA chefs

### Périmètre autorisé initial
- Destination initiale : uniquement l'adresse du propriétaire, après vérification et ajout explicite à une liste d'autorisation.
- Envoi possible 24 h/24 et 7 j/7, y compris la nuit, les week-ends et les jours fériés, si le propriétaire active le canal.
- Motifs autorisés : alerte critique, incident technique, opportunité commerciale documentée, demande de décision, rapport périodique ou compte rendu demandé.
- Les chefs peuvent initier un message sans sollicitation quotidienne, mais doivent fournir un motif, un niveau de priorité, des faits vérifiables et l'action attendue.
- Déduplication par clé d'idempotence ; limites de fréquence par agent et par catégorie ; regroupement des alertes répétitives.

### Interdictions
- Aucun e-mail à un prospect, client, fournisseur, partenaire ou autre tiers sans permission distincte et approbation du propriétaire.
- Aucun engagement contractuel, dépense, transfert, achat, retrait ou divulgation de données confidentielles par e-mail.
- Aucun envoi vers une adresse extraite librement d'un message ou d'un document.
- Aucun contournement de liste d'autorisation, quota, limite fournisseur ou politique de sécurité.
- Aucun secret, mot de passe, clé API, jeton, code OTP ou donnée bancaire dans le contenu.

### Permissions proposées
- `notify_owner_email` : notification au propriétaire seulement, adresse vérifiée et allowlistée ; activation explicite du canal par le propriétaire.
- `send_external_email` : tiers ; désactivé par défaut et soumis à approbation explicite par message.
- `voice_session` : session vocale interactive déclenchée par le propriétaire.
- `voice_speak` : synthèse vocale d'une réponse déjà autorisée.

Les permissions sont distinctes. L'autorisation de notifier le propriétaire ne doit jamais impliquer celle de contacter un tiers. Les actions externes existantes restent fermées tant que la politique ne les autorise pas.

## Priorité et disponibilité

- P0 — sécurité, panne critique, perte de données : notification immédiate.
- P1 — décision urgente ou opportunité à échéance proche : envoi rapide, avec échéance explicitée.
- P2 — rapport non urgent : envoi groupé selon la fréquence choisie.
- P3 — information : résumé périodique, pas de répétition inutile.

Le canal peut être disponible 24/7 sans imposer l'envoi de chaque événement. Les limites de fréquence protègent contre les boucles et les alertes en rafale. Le propriétaire peut suspendre le canal à tout moment.

## Enveloppe de message obligatoire

Chaque notification doit contenir au minimum :
- `notification_id` unique ;
- `agent_id` et rôle vérifiés ;
- `created_at` avec fuseau horaire ;
- `priority` et `reason_code` ;
- `recipient_class=owner` ;
- `subject` et `body` bornés ;
- `correlation_id` et `idempotency_key` ;
- `evidence_refs` vers les éléments internes qui justifient l'alerte ;
- `requires_owner_action` et, si nécessaire, `deadline`.

L'adresse e-mail réelle ne doit pas être librement choisie par l'agent : le routeur la résout depuis la configuration serveur vérifiée.

## Plan de réalisation — bloc de cinq jours

1. **Jour 1 — Contrats et gouvernance :** spécification des flux vocaux, de l'e-mail propriétaire, des permissions et des limites. (En cours de livraison dans ce commit.)
2. **Jour 2 — Interfaces techniques :** définir les protocoles STT/TTS/e-mail, les erreurs typées, les timeouts, les tests simulés et l'injection des fournisseurs.
3. **Jour 3 — Autorisation et routage :** implémenter la destination propriétaire allowlistée, la séparation stricte des permissions et la politique de priorité.
4. **Jour 4 — Résilience et audit :** idempotence, quotas, déduplication, reprise contrôlée, journalisation et mécanisme d'arrêt.
5. **Jour 5 — Validation :** tests de sécurité, tests d'intégration simulés, documentation d'exploitation et revue de préparation.

## Conditions d'activation

Aucune activation ne peut avoir lieu sans choix explicite du fournisseur, configuration des secrets hors dépôt, vérification de l'adresse du propriétaire, consentement aux modalités de traitement audio, validation de la politique, tests reproductibles et autorisation du propriétaire. Aucun secret ni accès fournisseur n'est demandé ou créé par cette phase documentaire.
