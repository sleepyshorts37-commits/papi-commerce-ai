# PKP-0001 — Spécification d'assemblage et préflight imprimable

**Version :** 1.0 — spécification, pas un PDF prêt à publier.  
**Dépendances :** manuscrit V1, storyboard 24 pages, brief illustration V1, revue éditoriale et registre d'assets.

## Décisions bloquantes avant mise en page

- Format de coupe KDP à choisir après vérification du type de livre, du nombre final de pages, du sens de lecture et des options d'impression disponibles.
- Le nombre final de pages doit respecter les contraintes courantes KDP pour le format et le type d'encre retenus.
- Fond perdu, marges intérieures, gouttière et dimensions de couverture doivent être calculés à partir du gabarit officiel KDP correspondant au format, papier, couverture et pagination définitifs.
- Le nom d'auteur, l'éditeur éventuel, l'ISBN et les mentions légales doivent être validés par le propriétaire ; ne rien inventer.
- Le canal de versement depuis le Sénégal demeure HOLD tant qu'il n'est pas vérifié pour le compte et la banque concernés.

## Architecture du paquet de fabrication

1. **Source éditoriale** : texte relu et approuvé, découpé page par page.
2. **Assets** : images originales identifiées, sources conservées, licences et validations consignées.
3. **Maquette intérieure** : une page de livre par page de sortie, texte éditable, illustrations placées sans distorsion.
4. **Export intérieur** : PDF haute qualité avec polices incorporées, pages au bon format et résolution contrôlée.
5. **Couverture** : fichier séparé calculé avec le gabarit exact KDP ; dos uniquement si le nombre de pages le permet.
6. **Préflight** : validation technique automatisée autant que possible, puis contrôle humain page par page.
7. **Épreuve** : aucune commande payante n'est autorisée dans le cadre zéro avance ; le contrôle écran et les validateurs gratuits ne remplacent pas une épreuve physique.
8. **Publication** : bloquée jusqu'à approbation éditoriale, graphique, juridique, économique, financière et humaine.

## Contrôles techniques obligatoires

- Dimensions exactes du format retenu ; aucune mise à l'échelle implicite.
- Images à résolution effective suffisante à la taille placée.
- Couleurs préparées selon les exigences officielles du produit d'impression choisi.
- Fond perdu uniquement lorsque requis ; aucun élément essentiel dans les zones de coupe.
- Marges et gouttière conformes au nombre de pages final.
- Polices incorporées et caractères correctement rendus.
- Pas de pages blanches accidentelles, objets hors page, transparences problématiques ou images manquantes.
- Texte lisible à taille réelle ; contraste adapté aux jeunes lecteurs.
- Vérification du sens de lecture, pagination, ordre des pages et cohérence des scènes.
- Couverture vérifiée séparément : dimensions, dos, tranche, zones de sécurité et code-barres laissées selon gabarit.
- Aucun contenu trompeur, promesse sanitaire, appel à s'approcher de l'eau ou représentation d'enfant manipulant déchets/objets dangereux.

## Résultat de préflight

Le préflight ne renvoie PASS que si chaque contrôle obligatoire est accompagné d'une preuve ou d'une vérification enregistrée. Les éléments inconnus renvoient HOLD ; ils ne sont pas assimilés à PASS.

États : `PASS`, `FAIL`, `HOLD`, `NOT_APPLICABLE`.

## Références à reconsulter au moment de la fabrication

- KDP — exigences de fichiers : https://kdp.amazon.com/en_US/help/topic/G200645690
- KDP — calculateur de couverture : https://kdp.amazon.com/cover-calculator
- KDP — formats et marges : https://kdp.amazon.com/en_US/help/topic/G201834180

Les spécifications évoluent : les gabarits doivent être téléchargés et recalculés au moment réel de la production. Ce document ne certifie aucune conformité KDP.
