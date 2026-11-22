# Mission 192 — Horodatages UTC canoniques pour les checkpoints d'audit

## Objectif

Empêcher deux représentations textuelles différentes d'un même instant d'être acceptées comme des checkpoints valides. Le protocole impose désormais une représentation unique : `YYYY-MM-DDTHH:MM:SSZ`.

## Changements

- Le décodeur exige le suffixe UTC `Z`.
- Il vérifie que le round-trip ISO 8601 à la seconde reproduit exactement la chaîne reçue.
- Les offsets `+00:00` ou non nuls, les fractions de seconde et les formats sans secondes sont refusés.
- Le test reconstruit des payloads JSON canoniques avec un digest SHA-256 valide pour isoler le contrôle du timestamp.
- La documentation de protocole et la roadmap précisent ce contrat.

## Validation

Les tests sont ajoutés et seront vérifiés par les workflows GitHub Actions déclenchés sur la PR. Aucun test local n'est déclaré dans ce rapport.

## Gouvernance et limites

- Changement limité au décodeur local et à ses tests.
- Aucun adaptateur distant, compte, secret, fournisseur, paiement ou déploiement.
- Aucun agent, worker permanent ou scheduler activé.
- PR brouillon empilée sur Mission 191 (#368), non fusionnée.
