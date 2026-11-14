# Charges utiles de synchronisation contrôlées

## Objet
La Mission 45 ajoute une charge utile séparée `.papidata` qui transporte le contenu des événements référencés par un bundle de synchronisation. Le bundle et son approbation Ed25519 continuent de définir l'autorité : chaque contenu doit reproduire exactement le `content_digest`, le type, l'identifiant et l'ordre approuvés.

## Contenus admis
- Mémoire : uniquement les événements `remember`, portée `shared`, sensibilité `normal`, auteur présent dans le registre d'agents. Les décisions officielles, mémoires privées/agent/owner et événements `supersede` sont exclus.
- PAPI CHAT : messages conformes au schéma existant, avec expéditeur et destinataire reconnus par le registre.
- Les motifs de secrets, adresses e-mail, numéros de téléphone sénégalais/internationaux courants et numéros de carte potentiels sont bloqués. Ce filtre est une défense complémentaire, pas une garantie de détection exhaustive des données personnelles.

## Liaison cryptographique
Pour chaque enregistrement, le SHA-256 canonique du document complet doit être égal au `content_digest` de l'événement correspondant. L'approbation Ed25519 existante signe le digest du bundle, qui contient ces empreintes et les IDs ordonnés. La charge utile ne peut donc pas substituer un contenu différent sans invalider la liaison au bundle approuvé.

Le fichier `.papidata` possède également son propre digest canonique, une version de format, une limite de 2 Mio et un nom dérivé de son digest.

## Stockage local
`write_sync_payload` crée un fichier sans écrasement dans un répertoire local protégé (0700), avec fichier 0600 et écriture atomique. `read_sync_payload` vérifie le fichier régulier, refuse les liens symboliques, contrôle l'encodage canonique, les doublons JSON, les tailles, la structure, les filtres et la correspondance au bundle.

## Exemple Python
```python
from pathlib import Path
from papi_core.sync_payload import write_sync_payload, read_sync_payload

staged = write_sync_payload(
    bundle=approved_bundle,
    records=[
        {"kind": "memory", "record": memory_event},
        {"kind": "message", "record": chat_message},
    ],
    spool_dir=Path("./outgoing-data"),
)
verified = read_sync_payload(
    Path(staged["path"]),
    bundle=approved_bundle,
)
```

## Limites
Cette mission prépare et vérifie le transfert du contenu, mais n'importe rien dans `events.jsonl` ou `messages.jsonl`. Elle ne consomme pas elle-même le nonce d'approbation et ne remplace pas la vérification Ed25519 du bundle par le récepteur Mission 44. Le récepteur doit valider le bundle et l'approbation avant tout usage de la charge utile. Aucun transport réseau, import atomique, fusion, suppression, worker, scheduler ou déploiement n'est activé.

Les filtres de confidentialité sont conservateurs mais ne peuvent pas reconnaître toutes les formes de données personnelles dans du texte libre. Une revue humaine du contenu exporté reste nécessaire.
