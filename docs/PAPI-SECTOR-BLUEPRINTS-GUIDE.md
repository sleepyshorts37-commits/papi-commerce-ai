# Guide — Modèles sectoriels PAPI WEB BUILDER

Le module `papi_core.sector_blueprints` fournit des plans de pages et des contrôles de préparation avant rédaction.

## Utilisation

```python
from papi_core.sector_blueprints import get_sector_blueprint, validate_sector_facts

blueprint = get_sector_blueprint("hospitality")
print(blueprint["pages"])
result = validate_sector_facts("hospitality", {
    # Renseigner chaque libellé de blueprint avec une information fournie
    # par le responsable de l'établissement.
})
```

Secteurs disponibles : `corporate`, `ecommerce`, `hospitality`, `professional_services`, `education`, `health`.

## Interprétation du contrôle
- `complete` indique que chaque libellé obligatoire possède une chaîne non vide.
- `missing_facts` énumère les éléments à demander.
- `truth_verified` reste toujours faux : le logiciel ne peut pas authentifier les déclarations.
- `human_verification_required` reste vrai.

Les recommandations de sections sont des indications de conception, pas du contenu publiable. Les textes, tarifs, disponibilités, qualifications, accréditations et résultats doivent être fournis et vérifiés avant publication.

## Garde-fous
- Santé : aucune promesse de guérison/efficacité, aucun diagnostic ou dosage.
- Commerce : prix, stock, promotions et livraison doivent être confirmés.
- Hôtellerie : disponibilité et tarifs ne sont jamais présentés comme temps réel sans intégration vérifiée.
- Éducation et services : ne pas inventer accréditations, diplômes, références ou garanties.
