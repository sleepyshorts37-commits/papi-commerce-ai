# Mission 161 — Contrôle de sécurité des manuscrits jeunesse

## Livrable
- Analyse lexicale hors réseau du manuscrit français page par page.
- Détection de formulations pouvant encourager l'entrée dans l'eau, la consommation d'eau inconnue, la manipulation de déchets/objets dangereux, l'absence d'adulte ou les déplacements près de berges instables.
- Alertes classées critical/high avec extraits contextualisés.
- Aucun verdict automatique : même sans alerte, une validation humaine est obligatoire.
- Attestation de revue signée logiquement par réviseur, date, preuve et SHA-256 exact du manuscrit.
- Si des alertes sont présentes, notes de résolution obligatoires avant attestation.

## Limites
Les règles lexicales peuvent produire des faux positifs ou manquer un contexte. Elles servent au triage, jamais à remplacer une relecture pédagogique, éditoriale et de sécurité par un adulte qualifié.
