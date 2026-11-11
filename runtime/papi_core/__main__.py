"""CLI de contrôle du registre PAPI."""
import argparse
import json
import sys
from .registry import RegistryError, route_department, validate_registries


def main() -> int:
    parser = argparse.ArgumentParser(prog="papi", description="Outils de contrôle PAPI COMMERCE AI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="Valider les registres agents et tâches")
    route = sub.add_parser("route", help="Lister les agents candidats d'un département")
    route.add_argument("department")
    args = parser.parse_args()
    try:
        if args.command == "validate":
            errors = validate_registries()
            if errors:
                print("\n".join(errors), file=sys.stderr)
                return 1
            print("OK — registres PAPI valides.")
            return 0
        print(json.dumps(route_department(args.department), ensure_ascii=False, indent=2))
        return 0
    except RegistryError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
