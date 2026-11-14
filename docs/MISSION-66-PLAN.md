# Mission 66 — PAPI Identity Registry Reconciliation & Drift Guard

## Ordre unique d'exécution — 20 journées regroupées

Cette mission suit obligatoirement la méthode standardisée de la Mission 65 : un seul ordre, vingt journées de travail, une seule branche, une seule PR et une exécution continue. Ne pas demander de validation intermédiaire pour les travaux de code, tests et documentation. Toute mutation réelle, activation ou synchronisation externe reste interdite sans autorisation distincte du propriétaire.

## Objectif

Construire une couche de rapprochement en lecture seule entre le registre canonique des agents (data/agents.json), le gestionnaire transactionnel de la Mission 65 et, à terme, les métadonnées d'identité Ed25519. Détecter les identités orphelines, les états divergents, les permissions incohérentes, les versions de clé anormales et les révisions invalides. Produire un rapport déterministe, traçable et exploitable par une revue humaine. En cas d'écart critique, recommander un état fail-closed ; ne jamais corriger automatiquement les registres.

## Travail des 20 jours

1. Inventorier les sources de vérité et documenter les champs disponibles.
2. Définir la hiérarchie entre registre canonique, journal transactionnel et archive cryptographique.
3. Définir les états comparables et les statuts de conception qui ne sont pas des activations.
4. Définir le contrat d'entrée/sortie du moteur de rapprochement.
5. Définir les catégories d'écarts, leur gravité et les règles fail-closed.
6. Implémenter une normalisation stricte et déterministe des identifiants.
7. Détecter les doublons et les entrées malformées sans choisir arbitrairement une identité.
8. Détecter les états transactionnels orphelins.
9. Détecter les identités canoniques actives/révoquées sans état transactionnel correspondant.
10. Détecter les activations transactionnelles d'agents seulement planifiés ou définis.
11. Détecter les divergences d'état active/revoked.
12. Détecter les divergences entre permissions autorisées.
13. Détecter les divergences entre permissions interdites, avec gravité critique.
14. Vérifier la cohérence des révisions et versions de clés.
15. Produire un rapport JSON stable avec compteurs, écarts triés et digest SHA-256.
16. Ajouter les tests unitaires des cas nominaux, doublons, écarts et données invalides.
17. Ajouter des tests de déterminisme et de fail-closed.
18. Documenter les limites, la hiérarchie de confiance et la procédure de résolution humaine.
19. Exécuter la suite de tests et les contrôles CI ; corriger les erreurs observées.
20. Mettre à jour la roadmap, rédiger le rapport final et ouvrir une PR brouillon unique.

## Livrables

- runtime/papi_core/identity_reconciliation.py
- tests/test_identity_reconciliation.py
- docs/MISSION-66-PLAN.md
- docs/MISSION-66-REPORT.md
- Mise à jour de docs/ROADMAP.md

## Critères d'acceptation

- Rapprochement en lecture seule, sans écriture dans aucun registre.
- Détection des entrées dupliquées, malformées, orphelines et absentes.
- Distinction explicite entre agents planifiés/définis et identités actives/révoquées.
- Détection des écarts d'état, permissions et interdictions.
- Validation des révisions et versions de clés.
- Rapport déterministe, trié, avec SHA-256.
- Fail-closed pour tout écart critique.
- Tests unitaires et CI verte sur le SHA exact de tête.

## Gouvernance

Aucune synchronisation automatique, correction, activation, révocation réelle, modification de permission, rotation de clé, appel réseau, accès Supabase, worker, scheduler, publication, prospection, paiement, dépense ou déploiement. Le moteur formule des constats ; l'humain décide et effectue toute correction autorisée. La PR reste en brouillon et n'est pas fusionnée.
