# Mission 142 — Estimateur de coût d'impression et de redevance KDP

## Référentiel officiel consulté le 15 novembre 2026
- Coût d'impression : https://kdp.amazon.com/en_US/help/topic/G201834340
- Redevance papier : https://kdp.amazon.com/en_US/help/topic/G201834330
- Formule KDP : (taux de redevance × prix catalogue) − coût d'impression.
- Taux Amazon : 50 % ou 60 % selon le prix et la marketplace ; Expanded Distribution : 40 % moins coût d'impression.
- Premium color 24–40 pages : coût fixe uniquement. Pour 8,5 × 8,5 po, le format est « large trim » ; Amazon.com affiche 4,20 USD pour 24–40 pages.
- À 42 pages et plus, le coût premium couleur large trim US devient 1,00 USD + 0,08 USD par page.
- Standard color commence à 72 pages ; premium color commence à 24 pages.
- Les prix et redevances restent dans la devise marketplace ; aucune conversion FCFA n'est faite.

## Livrables
- Calculateur multi-marketplaces pour les tables officielles vérifiées.
- Distinction regular/large trim selon les seuils KDP.
- Coût d'impression, seuil minimal estimé, palier de redevance, redevance estimée et mode Expanded Distribution.
- Décimales traitées avec Decimal ; rejet des prix hors seuil ou hors limites.
- Tests pour le livre de 24 pages, les paliers 50/60 %, le coût par page, Expanded Distribution et marketplace non supportée.

## Limites
Le calcul reste une estimation. Le coût et la redevance affichés dans l'écran KDP de configuration du titre font foi. Les taxes, retenues, conversion monétaire, éligibilité du compte sénégalais et prix finaux ne sont pas vérifiés.
