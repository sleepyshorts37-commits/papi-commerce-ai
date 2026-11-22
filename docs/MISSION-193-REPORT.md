# Mission 193 — Rejeter les clés JSON dupliquées dans le journal d'audit

## Constat

Le lecteur du journal utilisait le comportement JSON standard « dernière clé gagnante ». Une ligne pouvait donc contenir deux clés identiques, être décodée en un objet apparemment valide, puis passer le contrôle de hash si la dernière valeur correspondait à l'événement initial. Cela rendait le texte source ambigu malgré une chaîne de hash cohérente sur l'objet décodé.

## Modifications

- Ajoute un hook de décodage qui refuse les clés répétées dans tout objet JSON, y compris les objets imbriqués de `details`.
- Conserve la compatibilité avec les lignes historiques valides : aucun ordre de clés ni espacement canonique n'est imposé au journal existant.
- Ajoute une régression pour une clé dupliquée de premier niveau et une clé dupliquée imbriquée. Dans les deux cas, le test vérifie que le décodeur JSON standard produit le même objet apparent avant que le lecteur strict refuse la ligne.
- Actualise la documentation du journal et la roadmap.

## Validation

Les workflows GitHub Actions de la PR doivent exécuter les tests core, la validation des registres et les contrôles documentaires sur le SHA final. Aucun test local n'est déclaré dans cette session.

## Gouvernance et limites

- Branche dédiée empilée sur la tête de Mission 192 (#369).
- Aucun changement sur `main`, aucune fusion ni aucun déploiement.
- Aucun agent, worker ou scheduler réel activé.
- Aucun service externe, secret, compte, paiement ou effet commercial.
- Le hash local détecte les altérations par rapport à une chaîne connue, mais ne protège pas contre un attaquant contrôlant simultanément le journal et tous les checkpoints locaux.
