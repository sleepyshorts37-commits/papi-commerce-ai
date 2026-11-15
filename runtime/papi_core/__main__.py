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
from .kids_publishing import KidsPublishingError, build_catalog_report, check_book, load_catalog, validate_catalog
from .kids_project import KidsProjectError, create_project
from .kids_market_scoring import KidsMarketScoringError, build_market_report
from .kids_channel_routing import KidsChannelRoutingError, build_routing_report
from .kids_profitability import KidsProfitabilityError, build_profitability_report


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
    sub.add_parser("kids-validate", help="Valider le catalogue PAPI KIDS local")
    sub.add_parser("kids-report", help="Afficher le portefeuille de livres PAPI KIDS en lecture seule")
    kids_check = sub.add_parser("kids-check", help="Contrôler la préparation locale d'un livre")
    kids_check.add_argument("book_id")
    sub.add_parser("kids-market-report", help="Afficher le scoring de marché PAPI KIDS fondé sur des preuves")
    kids_route = sub.add_parser("kids-channel-route", help="Évaluer les canaux POD selon la règle zéro avance de trésorerie")
    kids_route.add_argument("--format", choices=["paperback", "ebook", "coloring_book", "illustrated_book", "activity_book"], required=True)
    kids_route.add_argument("--country", default="SN")
    kids_profit = sub.add_parser("kids-profitability", help="Calculer la marge unitaire à partir de coûts et preuves datées")
    kids_profit.add_argument("input_json", help="Chemin vers le fichier JSON de coûts documentés")
    kids_init = sub.add_parser("kids-init", help="Créer un kit de travail local vierge pour un nouveau livre")
    kids_init.add_argument("book_id")
    kids_init.add_argument("--title", required=True)
    kids_init.add_argument("--language", default="fr")
    kids_init.add_argument("--product-type", choices=["coloring_book", "illustrated_story", "educational_book", "activity_book", "ebook"], default="illustrated_story")
    kids_init.add_argument("--format", choices=["paperback", "ebook", "both"], default="paperback")
    kids_init.add_argument("--age-min", type=int, default=5)
    kids_init.add_argument("--age-max", type=int, default=8)
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
        if args.command == "kids-market-report":
            print(json.dumps(build_market_report(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "kids-channel-route":
            print(json.dumps(build_routing_report(args.format, args.country), ensure_ascii=False, indent=2))
            return 0
        if args.command == "kids-profitability":
            from pathlib import Path
            print(json.dumps(build_profitability_report(Path(args.input_json)), ensure_ascii=False, indent=2))
            return 0
        if args.command == "kids-init":
            print(json.dumps(create_project(
                args.book_id, args.title, args.language, args.product_type,
                args.format, args.age_min, args.age_max
            ), ensure_ascii=False, indent=2))
            return 0
        if args.command == "kids-validate":
            errors = validate_catalog(load_catalog())
            if errors:
                print("\\n".join(errors), file=sys.stderr)
                return 1
            print("OK — catalogue PAPI KIDS valide.")
            return 0
        if args.command == "kids-report":
            print(json.dumps(build_catalog_report(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "kids-check":
            result = check_book(args.book_id)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result.get("valid") else 1
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
    except (RegistryError, SchedulerError, SalesError, FinanceError, SecurityError, AccessDenied, KidsPublishingError, KidsProjectError, KidsMarketScoringError, KidsChannelRoutingError, KidsProfitabilityError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
