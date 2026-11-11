"""CLI de contrôle du registre et de planification PAPI."""
import argparse
import json
import sys

from .registry import RegistryError, route_department, validate_registries
from .orchestrator import build_dispatch_plan
from .doctor import diagnose_environment
from .command_center import build_command_center
from .scheduler import SchedulerError, due_schedules


def main() -> int:
    parser = argparse.ArgumentParser(prog="papi", description="Outils de contrôle PAPI COMMERCE AI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="Valider les registres agents et tâches")
    route = sub.add_parser("route", help="Lister les agents candidats d'un département")
    route.add_argument("department")
    sub.add_parser("plan", help="Préparer un plan consultatif des tâches en attente")
    sub.add_parser("doctor", help="Diagnostiquer la configuration locale sans réseau ni secret affiché")
    sub.add_parser("dashboard", help="Afficher PAPI COMMAND CENTER en lecture seule")
    sub.add_parser("schedule-preview", help="Afficher les échéances récurrentes à examiner, sans exécution")
    args = parser.parse_args()
    try:
        if args.command == "dashboard":
            print(json.dumps(build_command_center(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "doctor":
            print(json.dumps(diagnose_environment(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "schedule-preview":
            print(json.dumps(due_schedules(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "validate":
            errors = validate_registries()
            if errors:
                print("\\n".join(errors), file=sys.stderr)
                return 1
            print("OK — registres PAPI valides.")
            return 0
        if args.command == "route":
            print(json.dumps(route_department(args.department), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(build_dispatch_plan(), ensure_ascii=False, indent=2))
        return 0
    except (RegistryError, SchedulerError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
