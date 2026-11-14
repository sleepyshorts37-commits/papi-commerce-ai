"""Échange hors ligne de paquets sync signés : dépôt local, sans import ni réseau."""
from __future__ import annotations
import hashlib, json, os, re, stat, tempfile
from pathlib import Path
from typing import Any
from .sync_bundle import SyncBundleError, validate_sync_bundle
FORMAT_VERSION = 1
MAX_PACKAGE_BYTES = 2 * 1024 * 1024
_NAME = re.compile(r"^[a-f0-9]{64}\.papisync$")
class SyncSpoolError(ValueError):
    """Paquet hors ligne invalide ou stockage local non sûr."""
def _canonical(value: dict[str, Any]) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SyncSpoolError("Paquet non sérialisable de manière canonique.") from exc
def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result: raise SyncSpoolError("Clé JSON dupliquée.")
        result[key] = value
    return result
def _validate_package(bundle: object, approval: object) -> None:
    try: validate_sync_bundle(bundle)
    except (SyncBundleError, TypeError, KeyError) as exc: raise SyncSpoolError("Structure du paquet invalide.") from exc
    required = {"agent_id", "key_version", "timestamp", "nonce", "payload", "signature"}
    if not isinstance(approval, dict) or set(approval) != required: raise SyncSpoolError("Enveloppe d'approbation Ed25519 invalide.")
    if (not isinstance(approval["agent_id"], str) or not approval["agent_id"]
        or isinstance(approval["key_version"], bool) or not isinstance(approval["key_version"], int) or approval["key_version"] < 1
        or isinstance(approval["timestamp"], bool) or not isinstance(approval["timestamp"], int)
        or not isinstance(approval["nonce"], str) or len(approval["nonce"]) < 16
        or not isinstance(approval["signature"], str) or not re.fullmatch(r"[a-fA-F0-9]{128}", approval["signature"])
        or not isinstance(approval["payload"], dict)): raise SyncSpoolError("Champs d'approbation mal formés.")
    payload = approval["payload"]
    expected = {"scope":"papi.sync_bundle.import","decision":"approved","bundle_digest":bundle["bundle_digest"],
        "source_instance_id":bundle["source_instance_id"],"destination_instance_id":bundle["destination_instance_id"],
        "export_id":bundle["export_id"],"event_ids":[e["event_id"] for e in bundle["events"]]}
    if any(payload.get(k) != v for k,v in expected.items()): raise SyncSpoolError("L'approbation ne correspond pas au paquet.")
    if not isinstance(payload.get("approval_id"), str) or not payload["approval_id"].strip(): raise SyncSpoolError("Identifiant d'approbation absent.")
def _package_object(bundle, approval):
    _validate_package(bundle, approval)
    body = {"format_version":FORMAT_VERSION,"bundle":bundle,"approval":approval}
    return {**body,"package_digest":hashlib.sha256(_canonical(body)).hexdigest()}
def write_sync_package(*, bundle: dict[str, Any], approval: dict[str, Any], spool_dir: Path) -> dict[str, Any]:
    """Écrit atomiquement un paquet validé; refuse tout écrasement."""
    package = _package_object(bundle, approval); raw = _canonical(package)
    if len(raw) > MAX_PACKAGE_BYTES: raise SyncSpoolError("Paquet supérieur à la taille maximale autorisée.")
    spool_dir = Path(spool_dir); spool_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    if spool_dir.is_symlink() or not spool_dir.is_dir(): raise SyncSpoolError("Le répertoire spool doit être un dossier local réel.")
    os.chmod(spool_dir, 0o700); destination = spool_dir / (package["package_digest"] + ".papisync")
    fd, temporary = tempfile.mkstemp(prefix=".papi-sync-", suffix=".tmp", dir=spool_dir)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd,"wb") as handle:
            handle.write(raw); handle.flush(); os.fsync(handle.fileno())
        try: os.link(temporary,destination,follow_symlinks=False)
        except FileExistsError as exc: raise SyncSpoolError("Ce paquet existe déjà; aucun écrasement effectué.") from exc
        directory_fd=os.open(spool_dir,os.O_RDONLY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
    finally: Path(temporary).unlink(missing_ok=True)
    return {"status":"staged","path":str(destination),"package_digest":package["package_digest"],"size_bytes":len(raw),
        "signature_verified":False,"import_performed":False,"execution_enabled":False}
def read_sync_package(path: Path) -> dict[str, Any]:
    """Lit un fichier spool régulier et contrôle intégrité/structure; ne consomme aucun nonce."""
    path=Path(path)
    if not _NAME.fullmatch(path.name): raise SyncSpoolError("Nom de paquet non conforme.")
    try:
        fd=os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size<=0 or info.st_size>MAX_PACKAGE_BYTES:
                raise SyncSpoolError("Fichier absent, non régulier, vide ou trop volumineux.")
            chunks=[]; remaining=MAX_PACKAGE_BYTES+1
            while remaining:
                chunk=os.read(fd,min(65536,remaining))
                if not chunk: break
                chunks.append(chunk); remaining-=len(chunk)
            raw=b"".join(chunks)
            if len(raw)>MAX_PACKAGE_BYTES: raise SyncSpoolError("Paquet supérieur à la taille maximale autorisée.")
        finally: os.close(fd)
    except OSError as exc: raise SyncSpoolError("Paquet inaccessible ou lien symbolique refusé.") from exc
    try:
        package=json.loads(raw.decode("utf-8"),object_pairs_hook=_pairs_no_duplicates,
            parse_constant=lambda _: (_ for _ in ()).throw(SyncSpoolError("Constante JSON interdite.")))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc: raise SyncSpoolError("JSON du paquet invalide.") from exc
    if not isinstance(package,dict) or set(package)!={"format_version","bundle","approval","package_digest"} or package["format_version"]!=FORMAT_VERSION:
        raise SyncSpoolError("Version ou enveloppe du paquet invalide.")
    expected=hashlib.sha256(_canonical({"format_version":package["format_version"],"bundle":package["bundle"],"approval":package["approval"]})).hexdigest()
    if package["package_digest"]!=expected or path.name!=expected+".papisync": raise SyncSpoolError("Empreinte du paquet invalide ou nom incohérent.")
    _validate_package(package["bundle"],package["approval"])
    return {"bundle":package["bundle"],"approval":package["approval"],"package_digest":expected,"size_bytes":len(raw),
        "signature_verified":False,"nonce_consumed":False,"import_performed":False,"execution_enabled":False}
