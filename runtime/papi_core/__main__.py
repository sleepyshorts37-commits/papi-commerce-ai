"""CLI de contrôle du registre et de planification PAPI."""
import argparse
import json
import sys

from .registry import RegistryError, route_department, validate_registries
from .orchestrator import build_dispatch_plan
from .doctor import diagnose_environment
from .command_center import build_command_center
from .scheduler import SchedulerError, due_schedules
from .sales import SalesError, build_sales_report, load_sales
from .finance import FinanceError, finance_report, load_ledger
from .security import SecurityError, check_security
from .authz import AccessDenied, authorize_agent


def main() -> int:
    parser = argparse.ArgumentParser(prog="papi", description="Outils de contrôle PAPI COMMERCE AI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="Valider les registres agents et tâches")
    route = sub.add_parser("route", help="Lister les agents candidats d'un département")
    route.add_argument("department")
    agent_check = sub.add_parser("agent-check", help="Contrôler localement une permission d'agent")
    agent_check.add_argument("agent_id")
    agent_check.add_argument("permission")
    sub.add_parser("plan", help="Préparer un plan consultatif des tâches en attente")
    sub.add_parser("doctor", help="Diagnostiquer la configuration locale sans réseau ni secret affiché")
    sub.add_parser("dashboard", help="Afficher PAPI COMMAND CENTER en lecture seule")
    sub.add_parser("schedule-preview", help="Afficher les échéances récurrentes à examiner, sans exécution")
    sub.add_parser("sales-validate", help="Valider le registre commercial local")
    sub.add_parser("sales-report", help="Afficher le rapport commercial local en lecture seule")
    sub.add_parser("finance-validate", help="Valider le registre financier local")
    sub.add_parser("finance-report", help="Afficher le rapport financier local en lecture seule")
    sub.add_parser("security-check", help="Vérifier la posture de sécurité locale en lecture seule")
    args = parser.parse_args()
    try:
        if args.command == "agent-check":
            print(json.dumps(authorize_agent(args.agent_id, args.permission), ensure_ascii=False, indent=2))
            return 0
        if args.command == "dashboard":
            print(json.dumps(build_command_center(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "doctor":
            print(json.dumps(diagnose_environment(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "schedule-preview":
            print(json.dumps(due_schedules(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "sales-validate":
            load_sales()
            print("OK — registre commercial valide.")
            return 0
        if args.command == "sales-report":
            print(json.dumps(build_sales_report(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "finance-validate":
            load_ledger()
            print("OK — registre financier valide.")
            return 0
        if args.command == "finance-report":
            print(json.dumps(finance_report(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "security-check":
            print(json.dumps(check_security(), ensure_ascii=False, indent=2))
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
    except (RegistryError, SchedulerError, SalesError, FinanceError, SecurityError, AccessDenied, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
