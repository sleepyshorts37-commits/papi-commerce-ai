# Porte de contrôle — préparation à la production

Date de revue : 13 novembre 2026  
Périmètre : dépôt Git, code et tests automatisés disponibles.  
Décision : **NO-GO pour toute mise en production ou activation de workers interservices**.

Ce document distingue les contrôles présents dans le code des contrôles effectivement vérifiés dans un environnement déployé. Une CI verte ne vaut ni audit indépendant ni validation opérationnelle.

## Résumé des contrôles

| Domaine | État observé | Preuve / action requise |
|---|---|---|
| Exécution désactivée par défaut | PASS dans la configuration versionnée | `config/policy.json` fixe `execution_enabled=false`, budget à zéro et actions externes désactivées. Vérifier la configuration effective de chaque environnement avant lancement. |
| Authentification agent | PASS au niveau du code local | Vérification cryptographique Ed25519 et liaison à la tâche/au handler. Valider l'émetteur, la distribution et la révocation des clés dans l'environnement cible. |
| Binding service/audience | PARTIEL | `authorize_service_agent` et le mode strict du worker existent. Chaque worker exposé entre services doit être inventorié et configuré avec `require_service_audience=true`, `service_id` et `service_audience`. Le mode legacy reste compatible pour les workers locaux ; il ne doit pas servir de frontière interservice. |
| Gestion des clés d'audit | PARTIEL | Contrat fournisseur de signature et adaptateur local présents. Le keyring local n'est pas un KMS/HSM et ses clés privées ne sont pas chiffrées par mot de passe. Choisir et tester un stockage de clés isolé avant production. |
| Anti-rejeu / stockage partagé | PARTIEL | Adaptateur et contrat Supabase testés avec transport simulé. Aucun projet Supabase réel, rôle réel, RLS effective ni RPC distante n'a été validé. |
| Autorisations et approbations | PARTIEL | Contrôles locaux et refus des actions sensibles présents. Vérifier les permissions effectives et le parcours d'approbation de bout en bout avec identités et rôles réels. |
| Effets externes et finance | BLOQUÉ | Aucun fournisseur, compte marchand, secret ou flux de paiement ne doit être activé dans cette phase. Maintenir les actions externes/financières fermées et exiger une approbation humaine explicite. |
| Résilience et reprise | À VALIDER | Exécuter des tests de concurrence, perte de bail, crash avant/après effet métier, reprise et idempotence avec services de test. Ne pas annoncer une garantie exactly-once sans preuve. |
| Exploitation / restauration | À VALIDER | Définir alertes, rotation, sauvegardes, restauration, procédure d'arrêt d'urgence, journalisation et responsabilités d'astreinte. |
| Revue indépendante | BLOQUÉ | Faire réaliser une revue indépendante et un test d'intrusion avant exposition publique ou données réelles. |

## Conditions obligatoires de levée du NO-GO

1. **Inventaire des workers** : recenser chaque worker, son exposition réseau, son service propriétaire, son audience et son mode d'authentification. Aucun worker exposé ne doit rester en mode legacy.
2. **Identité workload** : choisir un mécanisme de confiance pour authentifier les services (OIDC/workload identity ou équivalent), protéger les clés, définir rotation, révocation et moindre privilège.
3. **Clés d'audit** : sélectionner un KMS/HSM ou service de signature isolé, tester les droits d'accès, la disponibilité, la rotation et la révocation.
4. **Supabase réel de test** : créer un environnement isolé, exécuter les migrations uniquement après revue, vérifier RLS et grants avec les rôles applicatifs, tester l'anti-rejeu concurrent et les échecs réseau.
5. **Tests de bout en bout** : tester tâches autorisées/refusées, audiences substituées, identité révoquée, nonce rejoué, approbation manquante, perte de bail, reprise après crash et arrêt d'urgence.
6. **Protection des données** : classifier les données, minimiser les champs, définir rétention/suppression, vérifier les journaux et les sauvegardes sans secrets ni données personnelles excessives.
7. **Exploitation** : documenter surveillance, alertes, rotation des secrets, sauvegarde/restauration, réponse aux incidents et retour arrière.
8. **Revue indépendante** : corriger les constats critiques/élevés et obtenir une validation formelle avant ouverture des flux externes.
9. **Activation contrôlée** : commencer par un environnement de préproduction avec données fictives et handlers non sensibles. Toute dépense, souscription, publication, prospection ou transaction exige une autorisation distincte du propriétaire.

## Contrôles de sécurité à conserver

- Ne jamais stocker de secrets dans Git, prompts, journaux ou fichiers de configuration versionnés.
- Ne pas activer workers, scheduler permanent, communications externes ou opérations financières par défaut.
- Ne pas effectuer de migration sur une base réelle dans le cadre de cette revue.
- Ne pas confondre PR ouverte, tests CI réussis et déploiement validé.
- Une erreur d'authentification, de signature, de politique ou de configuration doit conduire à un refus fermé.

## Conclusion

Le dépôt dispose de briques de sécurité et de tests utiles, mais les preuves actuelles sont principalement locales et simulées. **Le projet n'est pas certifié prêt pour la production.** Le passage en production dépend des validations workload/KMS, Supabase réel, tests de bout en bout, exploitation et audit indépendant ci-dessus.

Cette porte de contrôle est une checklist de décision, pas une activation automatique ni une autorisation de déployer.
