"""CLI de contrôle du registre et de planification PAPI."""
import argparse
import json
import sys

from .registry import RegistryError, route_department, validate_registries, validate_agent_directory
from .orchestrator import build_dispatch_plan
from .doctor import diagnose_environment
from .command_center import build_command_center
from .scheduler import SchedulerError, due_schedules
from .sales import SalesError, build_sales_report, load_sales
from .finance import FinanceError, finance_report, load_ledger
from .security import SecurityError, check_security
from .authz import AccessDenied, authorize_agent
from .supabase_preflight import run_supabase_preflight, require_supabase_configuration
from .sync_receiver import receive_sync_package
from .sync_import import import_approved_sync_content
from .jsonl_migration import migrate_jsonl_to_sqlite, MigrationError
from .sqlite_backup import create_sqlite_backup, verify_sqlite_backup, restore_sqlite_backup, BackupRestoreError
from .sqlite_backup_crypto import (generate_backup_key, encrypt_sqlite_backup, verify_encrypted_backup, decrypt_sqlite_backup, rotate_encrypted_backup_key, BackupEncryptionError)


def main() -> int:
    parser = argparse.ArgumentParser(prog="papi", description="Outils de contrôle PAPI COMMERCE AI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="Valider les registres agents et tâches")
    sub.add_parser("organization-check", help="Valider les identités et la cohérence de l'organigramme")
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
    receiver = sub.add_parser("receive-sync-package", help="Authentifier un paquet .papisync et inscrire un reçu local sans importer de contenu")
    receiver.add_argument("--package", required=True, help="Chemin du fichier .papisync reçu")
    receiver.add_argument("--owner-id", required=True, help="Identifiant du propriétaire autorisé")
    receiver.add_argument("--registry", required=True, help="Chemin du registre local de clés publiques")
    receiver.add_argument("--ledger", required=True, help="Chemin du registre SQLite local des reçus")
    receiver.add_argument("--destination", required=True, help="Identifiant exact de cette instance destinataire")
    importer = sub.add_parser("import-sync-content", help="Importer atomiquement le contenu d'un paquet approuvé dans SQLite local")
    importer.add_argument("--package", required=True, help="Chemin du fichier .papisync")
    importer.add_argument("--payload", required=True, help="Chemin du fichier .papidata")
    importer.add_argument("--owner-id", required=True, help="Identifiant du propriétaire autorisé")
    importer.add_argument("--registry", required=True, help="Registre local de clés publiques")
    importer.add_argument("--ledger", required=True, help="Base SQLite locale de reçus et contenus importés")
    importer.add_argument("--destination", required=True, help="Identifiant exact de cette instance")
    importer.add_argument("--agents", required=True, help="Registre local des agents")
    migrate = sub.add_parser("migrate-jsonl", help="Sauvegarder puis migrer un journal JSONL local vers SQLite")
    migrate.add_argument("--kind", choices=("memory", "message"), required=True)
    migrate.add_argument("--source", required=True)
    migrate.add_argument("--database", required=True)
    migrate.add_argument("--backup-dir", required=True)
    migrate.add_argument("--agents", default="data/agents.json")
    backup = sub.add_parser("sqlite-backup", help="Créer une sauvegarde cohérente et vérifiée d'une base SQLite locale")
    backup.add_argument("--database", required=True)
    backup.add_argument("--backup-dir", required=True)
    verify_backup = sub.add_parser("sqlite-backup-verify", help="Vérifier une sauvegarde SQLite via son manifeste")
    verify_backup.add_argument("--manifest", required=True)
    restore = sub.add_parser("sqlite-restore", help="Restaurer une sauvegarde vers un nouveau chemin sans écrasement")
    restore.add_argument("--manifest", required=True)
    restore.add_argument("--destination", required=True)
    keygen = sub.add_parser("sqlite-keygen", help="Générer une clé locale AES-256 dans un fichier exclusif")
    keygen.add_argument("--key-file", required=True)
    encrypt = sub.add_parser("sqlite-backup-encrypt", help="Chiffrer un snapshot SQLite avec AES-256-GCM")
    encrypt.add_argument("--backup", required=True)
    encrypt.add_argument("--key-file", required=True)
    encrypt.add_argument("--manifest", required=True)
    verify_enc = sub.add_parser("sqlite-backup-verify-encrypted", help="Authentifier et vérifier une sauvegarde chiffrée")
    verify_enc.add_argument("--manifest", required=True)
    verify_enc.add_argument("--key-file", required=True)
    decrypt = sub.add_parser("sqlite-backup-decrypt", help="Déchiffrer vers un nouveau fichier SQLite")
    decrypt.add_argument("--manifest", required=True)
    decrypt.add_argument("--key-file", required=True)
    decrypt.add_argument("--destination", required=True)
    rotate = sub.add_parser("sqlite-backup-rotate-key", help="Ré-encrypter une sauvegarde avec une nouvelle clé")
    rotate.add_argument("--manifest", required=True)
    rotate.add_argument("--old-key-file", required=True)
    rotate.add_argument("--new-key-file", required=True)
    rotate.add_argument("--new-manifest", required=True)
    preflight = sub.add_parser("supabase-preflight", help="Contrôler les migrations et la configuration Supabase sans réseau")
    preflight.add_argument("--require-configured", action="store_true", help="Exiger URL et clé serveur configurées")
    args = parser.parse_args()
    try:
        if args.command == "organization-check":
            report = validate_agent_directory()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["valid"] else 1
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
        if args.command == "receive-sync-package":
            report = receive_sync_package(
                package_path=args.package, owner_id=args.owner_id,
                registry_path=args.registry, ledger_db=args.ledger,
                expected_destination=args.destination,
            )
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if args.command == "import-sync-content":
            report = import_approved_sync_content(
                package_path=args.package, payload_path=args.payload,
                owner_id=args.owner_id, registry_path=args.registry,
                ledger_db=args.ledger, expected_destination=args.destination,
                agents_path=args.agents,
            )
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if args.command == "migrate-jsonl":
            report = migrate_jsonl_to_sqlite(
                kind=args.kind, source_path=args.source, database_path=args.database,
                backup_dir=args.backup_dir, agents_path=args.agents,
            )
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if args.command == "sqlite-backup":
            report = create_sqlite_backup(args.database, args.backup_dir)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if args.command == "sqlite-backup-verify":
            report = verify_sqlite_backup(args.manifest)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if args.command == "sqlite-restore":
            report = restore_sqlite_backup(args.manifest, args.destination)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if args.command == "sqlite-keygen":
            report = generate_backup_key(args.key_file)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if args.command == "sqlite-backup-encrypt":
            report = encrypt_sqlite_backup(args.backup, args.key_file, args.manifest)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if args.command == "sqlite-backup-verify-encrypted":
            report = verify_encrypted_backup(args.manifest, args.key_file)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if args.command == "sqlite-backup-decrypt":
            report = decrypt_sqlite_backup(args.manifest, args.key_file, args.destination)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if args.command == "sqlite-backup-rotate-key":
            report = rotate_encrypted_backup_key(args.manifest, args.old_key_file, args.new_key_file, args.new_manifest)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if args.command == "supabase-preflight":
            report = run_supabase_preflight()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if args.require_configured:
                require_supabase_configuration(report)
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
    except (RegistryError, SchedulerError, SalesError, FinanceError, SecurityError, AccessDenied, MigrationError, BackupRestoreError, BackupEncryptionError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
