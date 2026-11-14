# Mission 40 — Plan de travail sur cinq jours

1. **Jour 1 — Audit sécurité :** vérifier les contrats des paquets, le registre Ed25519 et l'anti-rejeu existants; formaliser les menaces et limites.
2. **Jour 2 — Signature :** développer l'attestation Ed25519 qui lie digest, origine, destination, export et identifiants ordonnés.
3. **Jour 3 — Vérification :** appliquer le contrôle propriétaire, le scope strict, la destination attendue, l'intégrité et le TTL.
4. **Jour 4 — Tests :** ajouter les tests positifs et adversariaux, notamment rejeu, altération, mauvaise identité et approbation hors délai.
5. **Jour 5 — Livraison :** documenter l'exploitation, mettre à jour la roadmap sans cocher la synchronisation réelle, lancer CI et préparer la PR brouillon.

**Livrables :** module `sync_bundle_approval.py`, tests dédiés, contrat opérateur, prompt, plan et rapport final.

**Garde-fous :** aucune clé privée dans Git, aucun transfert ou import, aucune consommation distante, aucun déploiement ni action externe.
