# Guide — générateur de contenus commerciaux PAPI

Le module papi_core.content_generation produit des brouillons structurés à partir d'un brief local. Il ne sollicite aucun modèle IA et n'effectue aucune action externe.

## Contrat
- Types : product, service, business_page, social_post.
- Secteurs : pharmacy, hotel, restaurant, retail, professional_services.
- Tons : professional, friendly, premium, concise.
- Champs requis : content_type, sector, brand, offer, facts.
- Champs facultatifs : audience, tone, cta.
- De 1 à 8 faits, 180 caractères maximum par fait.

## Règles
- Le moteur reprend exclusivement les informations du brief ; il n'invente ni prix, disponibilité, certification, avis, performance ni caractéristique.
- Les champs inconnus, balisages, textes vides ou trop longs sont refusés.
- Les allégations explicites de guérison, d'efficacité garantie et de résultats garantis sont refusées.
- Pour la pharmacie, les dosages sont refusés et une mention invite à consulter un professionnel de santé.
- Pour l'hôtellerie, tarifs et disponibilités doivent être confirmés.
- Pour la restauration, ingrédients et allergènes doivent être confirmés.
- Chaque sortie porte review_required=true.

## Limites
Ce composant est un moteur de structuration et de rédaction par modèles déterministes, pas un générateur LLM. Les contenus sont des brouillons. Une personne doit vérifier les informations, droits, prix, conditions et règles applicables avant publication. Aucune publication, prospection ou transaction n'est exécutée.