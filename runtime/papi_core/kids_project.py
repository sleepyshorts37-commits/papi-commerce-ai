"""Create safe, local production packs for PAPI KIDS book projects.

The generator creates editable working templates only. It does not generate
finished editorial content, artwork, PDFs, KDP metadata for submission, or
perform any external action.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROJECTS_ROOT = ROOT / "workspace" / "papi-kids"
BOOK_ID_RE = re.compile(r"^PKP-[A-Z0-9]{4,20}$")
LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})?$")
PRODUCT_TYPES = {"coloring_book", "illustrated_story", "educational_book", "activity_book", "ebook"}
FORMATS = {"paperback", "ebook", "both"}


class KidsProjectError(ValueError):
    """Invalid project input or unsafe output destination."""


def _validate_input(book_id: str, title: str, language: str, product_type: str,
                    book_format: str, age_min: int, age_max: int) -> None:
    if not isinstance(book_id, str) or not BOOK_ID_RE.fullmatch(book_id):
        raise KidsProjectError("book_id doit respecter PKP- suivi de 4 à 20 caractères A-Z/0-9.")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 200:
        raise KidsProjectError("Le titre doit contenir entre 1 et 200 caractères.")
    if not isinstance(language, str) or not LANGUAGE_RE.fullmatch(language):
        raise KidsProjectError("Code de langue invalide, exemple : fr ou en.")
    if not isinstance(product_type, str) or product_type not in PRODUCT_TYPES:
        raise KidsProjectError("Type de livre non pris en charge.")
    if not isinstance(book_format, str) or book_format not in FORMATS:
        raise KidsProjectError("Format non pris en charge.")
    if isinstance(age_min, bool) or isinstance(age_max, bool) or not isinstance(age_min, int) or not isinstance(age_max, int):
        raise KidsProjectError("Les âges doivent être des entiers.")
    if not (0 <= age_min <= age_max <= 18):
        raise KidsProjectError("Tranche d'âge invalide : valeurs de 0 à 18, minimum inférieur ou égal au maximum.")


def _reject_symlink_components(path: Path) -> None:
    absolute = Path(path).absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise KidsProjectError("Destination refusée : composant symbolique détecté.")


def _project_files(book_id: str, title: str, language: str, product_type: str,
                   book_format: str, age_min: int, age_max: int) -> dict[str, str]:
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "book_id": book_id,
        "title": title.strip(),
        "language": language,
        "product_type": product_type,
        "format": book_format,
        "target_age_min": age_min,
        "target_age_max": age_max,
        "publication_status": "not_submitted",
        "human_approval_required": True,
        "external_submission_performed": False,
    }
    metadata_text = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    checklist = """# Liste de contrôle de production

## Concept et recherche
- [ ] Public cible et besoin lecteur documentés
- [ ] Positionnement et différenciation documentés
- [ ] Concept original approuvé en interne
- [ ] Aucun élément protégé repris sans licence valable

## Droits et contenu enfant
- [ ] Vérification préliminaire des noms, personnages, marques et licences
- [ ] Sources et licences des éléments tiers consignées
- [ ] Adaptation à l'âge et sécurité du contenu vérifiées

## Production
- [ ] Manuscrit terminé et relu
- [ ] Illustrations originales terminées et vérifiées
- [ ] Maquette intérieure exportée et contrôlée
- [ ] Couverture et dos calculés selon le gabarit actuel de la plateforme
- [ ] Métadonnées revues

## Contrôle final
- [ ] Contrôle indépendant de l'orthographe, pagination, marges et lisibilité
- [ ] Contrôle technique du format et des fichiers finaux
- [ ] Exigences actuelles de la plateforme vérifiées
- [ ] Coûts, prix, redevances et marge estimés sans promesse de vente
- [ ] Validation humaine explicite enregistrée

Aucune case cochée automatiquement. Cette liste ne constitue pas une validation juridique ou une garantie d'acceptation par une plateforme.
"""
    brief = f"""# Brief éditorial — {title.strip()}

- Identifiant : {book_id}
- Langue : {language}
- Type : {product_type}
- Format cible : {book_format}
- Âge cible : {age_min}–{age_max} ans
- Statut : cadrage initial, non validé

## Promesse lecteur
À définir : quel bénéfice concret et adapté à l'âge ce livre apporte-t-il ?

## Besoin et différenciation
À documenter à partir de recherches vérifiables. Ne pas inventer de chiffres de demande, de ventes ou de concurrence.

## Concept original
À rédiger. Utiliser uniquement des personnages, noms, histoires et illustrations originaux ou dûment licenciés.

## Plan détaillé
À compléter avec les chapitres, activités ou séquences, objectifs pédagogiques et progression.

## Direction artistique
À définir : palette, ambiance, cohérence des personnages, lisibilité et contraintes d'impression.

## Sources et droits
À compléter : sources consultées, licences, autorisations et éléments à faire vérifier.

## Critères de réussite
À définir avant la rédaction : exactitude, lisibilité, intérêt, sécurité et adéquation à l'âge.
"""
    manuscript = f"""# {title.strip()}

> BROUILLON DE TRAVAIL — aucun contenu final n'est fourni par ce modèle.
> Langue : {language} | Public : {age_min}–{age_max} ans

## Page de titre
À compléter.

## Note aux lecteurs / parents
À rédiger après validation éditoriale.

## Contenu
Insérer ici le manuscrit original, relu et adapté à la tranche d'âge.

## Sources et crédits
Lister les sources et les crédits/licences nécessaires.
"""
    quality = {
        "schema_version": 1,
        "book_id": book_id,
        "review_status": "pending",
        "reviewer": None,
        "reviewed_at": None,
        "checks": {
            "age_appropriateness": "pending",
            "originality_and_rights": "pending",
            "editorial_accuracy": "pending",
            "language_and_spelling": "pending",
            "layout_and_readability": "pending",
            "platform_technical_requirements": "pending",
        },
        "issues": [],
        "note": "Modèle vierge ; aucun contrôle qualité n'a été effectué.",
    }
    return {
        "README.md": f"# {title.strip()}\n\nProjet PAPI KIDS {book_id}.\n\nDossier de travail local créé à partir de modèles vierges. Aucun manuscrit final, aucune illustration, aucun PDF et aucune validation ne sont fournis.\n",
        "brief.md": brief,
        "manuscript.md": manuscript,
        "metadata.json": metadata_text,
        "production-checklist.md": checklist,
        "quality-report.json": json.dumps(quality, ensure_ascii=False, indent=2) + "\n",
    }


def create_project(book_id: str, title: str, language: str = "fr",
                   product_type: str = "illustrated_story", book_format: str = "paperback",
                   age_min: int = 5, age_max: int = 8,
                   output_root: Path = PROJECTS_ROOT) -> dict[str, Any]:
    """Create a new, non-overwriting project pack inside a caller-selected root."""
    _validate_input(book_id, title, language, product_type, book_format, age_min, age_max)
    output_root = Path(output_root)
    _reject_symlink_components(output_root)
    try:
        output_root.mkdir(parents=True, exist_ok=True)
        root = output_root.resolve(strict=True)
        if not root.is_dir():
            raise KidsProjectError("La destination doit être un dossier.")
        target = root / book_id
        if target.exists() or target.is_symlink():
            raise KidsProjectError("Un projet existe déjà avec cet identifiant ; aucun fichier n'a été modifié.")
        target.mkdir()
        files = _project_files(book_id, title, language, product_type, book_format, age_min, age_max)
        try:
            for relative, body in files.items():
                destination = target / relative
                with destination.open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(body)
        except Exception:
            shutil.rmtree(target, ignore_errors=True)
            raise
    except KidsProjectError:
        raise
    except OSError as exc:
        raise KidsProjectError("Impossible de créer le dossier de production local.") from exc

    return {
        "book_id": book_id,
        "title": title.strip(),
        "project_path": str(target),
        "created_files": sorted(files),
        "file_count": len(files),
        "catalog_updated": False,
        "external_actions_performed": False,
        "note": "Kit de travail vierge uniquement ; aucun contenu final ni fichier KDP prêt à publier.",
    }
