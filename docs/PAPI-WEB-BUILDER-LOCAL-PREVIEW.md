# Aperçu local isolé — PAPI WEB BUILDER

Le module `papi_core.preview_server` fournit un serveur HTTP de prévisualisation **local et en lecture seule** pour un site statique déjà généré.

## Utilisation

```python
from papi_core.preview_server import create_preview_server

server = create_preview_server("/chemin/vers/site-genere", host="127.0.0.1", port=0)
try:
    print(f"Aperçu local : http://127.0.0.1:{server.server_port}/")
    server.serve_forever()
finally:
    server.server_close()
```

Le serveur n'est pas démarré par le constructeur : l'appelant contrôle explicitement son cycle de vie. Le port `0` demande au système un port libre.

## Mesures de sécurité

- Liaison exclusivement à une adresse IP loopback ; les adresses réseau publiques et `0.0.0.0` sont refusées.
- Méthodes GET et HEAD uniquement ; POST, PUT, PATCH et DELETE sont refusées.
- Résolution stricte des chemins, refus de traversée de répertoire et de liens symboliques.
- Pas de listing de répertoire ; seuls les fichiers réguliers sous la racine de prévisualisation sont servis.
- CSP restrictive sans scripts, `nosniff`, cache désactivé et politique de référent sans transmission.

## Limites et statut

C'est un serveur local de fichiers statiques, pas un bac à sable de code arbitraire. Les pages générées ne doivent pas contenir de scripts tiers. Aucune publication Internet, aucun domaine, aucun hébergement, aucun moteur de capture d'écran ni navigateur automatisé n'est activé. Le serveur n'effectue pas lui-même de rendu navigateur : ouvrir l'URL dans un navigateur local reste une action distincte.

Les tests automatisés couvrent le service de pages imbriquées, les assets, les en-têtes de sécurité, les méthodes d'écriture, la traversée de chemin, les liens symboliques et le refus des interfaces non-loopback.
