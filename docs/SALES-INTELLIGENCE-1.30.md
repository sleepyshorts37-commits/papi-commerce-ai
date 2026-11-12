# PAPI SALES INTELLIGENCE — Phase 1.30

## Objectif
Analyser les résultats commerciaux agrégés par activité PAPI, segment de clientèle et canal afin d'aider à choisir où tester une offre. Le moteur traite uniquement des métriques agrégées et non nominatives.

## Données acceptées
- Activité : PAPI MARKET, PAPI DROPSHIPPING, PAPI AFFILIATION, PAPI FREELANCE, PAPI SERVICES ou PAPI BUSINESS PARTNERS.
- Marché, segment client et offre.
- Canal : WhatsApp, Instagram, Facebook, TikTok, site web, e-mail, téléphone, marketplace, présentiel, recommandation ou autre.
- Type de source, URL HTTPS et date d'observation avec fuseau horaire.
- Nombre de demandes entrantes ; nombres facultatifs de prospects qualifiés, ventes et dépenses de campagne en XOF.
- Fenêtre d'observation de 1 à 365 jours.

Aucun nom, numéro de téléphone, adresse e-mail, identifiant de compte ou liste de prospects n'est accepté. Ne pas soumettre de données individuelles.

## Mesures calculées
- Taux de qualification = prospects qualifiés / demandes entrantes.
- Taux de transformation = ventes / prospects qualifiés.
- Coût par prospect qualifié = dépenses observées / prospects qualifiés.
- Comparaison descriptive des canaux à partir des observations récentes : nombre de prospects qualifiés observé, puis coût par prospect qualifié.

Les dénominateurs nuls ou données manquantes produisent une valeur inconnue, jamais une estimation artificielle. Les canaux sont classés sur les seuls résultats observés, pas sur une prévision.

## Command Center
Le paramètre facultatif `sales_observations` alimente la section `sales_intelligence`. Les observations sont regroupées par activité, marché et segment.

## Limites et garde-fous
- Les URL ne sont pas consultées ; les données sources ne sont pas vérifiées indépendamment.
- Les demandes observées ne représentent ni la demande totale du marché ni une part de marché.
- Un échantillon faible ou biaisé ne prouve pas la performance future d'un canal.
- Aucun prospect n'est identifié ou contacté.
- Aucun message, campagne, achat, dépense ou action commerciale n'est lancé.
- Aucun chiffre d'affaires futur n'est inventé.

## Vérification
Tests ajoutés dans `tests/test_sales_intelligence.py`, non exécutés dans cet environnement. CI à vérifier sur la PR. Cette phase ne déploie aucun agent et n'active aucun worker.
