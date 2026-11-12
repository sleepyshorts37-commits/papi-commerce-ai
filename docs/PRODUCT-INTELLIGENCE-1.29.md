# PAPI PRODUCT INTELLIGENCE — Phase 1.29

## Objectif
Comparer des options de produits et fournisseurs à partir de devis, catalogues et observations publiques fournis au système. Calculer un coût unitaire complet et une marge brute indicative uniquement lorsque les données nécessaires sont présentes.

## Données acceptées
Chaque observation comprend le produit, le marché, le fournisseur, le type de source, une URL HTTPS, la date d'observation avec fuseau horaire et le prix d'achat unitaire en XOF. Les postes facultatifs sont : transport, taxes, emballage, frais de plateforme, prix de vente, quantité minimale, délai de livraison et notes.

Les montants dans une autre devise sont rejetés dans cette version. Ne pas fournir de coordonnées privées, identifiants, mots de passe ou informations personnelles.

## Calculs
Le coût unitaire complet est calculé uniquement si les cinq postes sont renseignés :
- achat
- transport
- taxes
- emballage
- frais de plateforme

Un poste manquant reste inconnu ; il n'est jamais supposé égal à zéro. La marge brute indicative est calculée uniquement avec un coût complet et un prix de vente connu ou un prix cible fourni. Elle ne constitue pas un bénéfice net et n'inclut pas automatiquement les retours, garanties, pertes, coûts fixes ou frais non renseignés.

## Comparaison fournisseurs
Les observations sont regroupées par produit et marché. Seuls les coûts unitaires complets en XOF sont classés. La similarité des spécifications, qualité, quantité minimale, authenticité, garanties, douane et conditions de livraison doit être vérifiée par une personne avant décision.

## Command Center
Le paramètre facultatif `product_observations` alimente la section `product_intelligence`. Le paramètre facultatif `target_product_selling_price_xof` permet de calculer une marge indicative lorsque le prix de vente n'est pas présent dans le devis.

## Limites et sécurité
- Aucune URL n'est visitée ; les devis et sources ne sont pas vérifiés indépendamment.
- Aucun fournisseur n'est contacté.
- Aucun scraping, achat, paiement, publicité ou dépense.
- Aucune commande ni action commerciale n'est exécutée.
- Les résultats sont des estimations documentaires, pas une validation de demande ou de rentabilité réelle.

## Vérification
Des tests sont ajoutés dans `tests/test_product_intelligence.py`, mais ils n'ont pas été exécutés dans cet environnement. L'état CI doit être vérifié sur la PR. Aucun agent n'est déployé et aucun worker n'est activé par cette proposition.
