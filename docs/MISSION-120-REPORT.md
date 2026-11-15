# Mission 120 — preuve de quota et verrou d'exécution

## But
Remplacer le simple booléen \`free_quota_confirmed\` par une attestation structurée, liée au compte Cloudflare et au modèle exact, vérifiée lors de la planification puis à nouveau avant toute soumission.

## Implémentation
- \`runtime/papi_core/image_quota_evidence.py\` valide fournisseur, compte, modèle, URL officielle Cloudflare HTTPS, référence de preuve, horodatages, expiration, quota journalier, coût estimé, taille de campagne et plafond monétaire égal à zéro.
- Une preuve de plus de 24 heures est rejetée.
- Le quota annoncé doit couvrir l'estimation de toute la campagne.
- À l'exécution, le modèle doit être présent dans le routeur gratuit, le coût doit correspondre à celui de l'adaptateur et le plafond journalier doit correspondre à celui du ledger configuré.
- L'identifiant de preuve doit être identique entre la préparation et l'exécution ; toute modification oblige à refaire le plan.
- L'adaptateur Cloudflare continue de réserver chaque image dans son ledger avant l'appel fournisseur. Les réservations transactionnelles sont le dernier verrou contre le dépassement et la concurrence inter-workers.

## Limite essentielle — pas de fausse garantie
Cette mission ne crée pas une API Cloudflare de lecture du quota du compte et ne prétend pas que l'attestation constitue une vérification automatique par Cloudflare. C'est une preuve opérateur documentée, datée et limitée dans le temps. La réponse API officielle et le ledger transactionnel doivent encore confirmer la réservation au moment de chaque génération. Le ledger local en mémoire ne doit pas être considéré comme une autorité partagée ; utiliser le ledger Supabase transactionnel déjà présent lorsque plusieurs workers sont actifs.

L'URL doit pointer vers la documentation officielle, mais la présence de cette URL ne prouve pas à elle seule l'éligibilité gratuite du compte. Il faut vérifier manuellement le compte, le modèle, les limites et les conditions en vigueur. Aucun modèle n'est activé automatiquement par cette mission.

## Tests
Tests unitaires sans réseau : preuve absente, preuve périmée, compte/modèle/quota discordants, campagne au-dessus du quota, plafond non nul, planification 24 scènes et blocage d'exécution sans adaptateur/ledger réel. Aucun appel Cloudflare, aucune clé, aucune dépense.

## Sécurité inchangée
Dépenses plafonnées à zéro ; aucune bascule payante ; autorisation explicite requise ; génération et publication non déclenchées ; revue humaine toujours obligatoire.
