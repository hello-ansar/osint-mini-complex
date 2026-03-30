import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


EMAIL_STATUSES = {"registered", "not registered", "error"}
USERNAME_STATUSES = {"found", "not found", "error"}


@dataclass
class ScanRecord:
    scan_type: str               # "email" | "username"
    target: str
    platform: str
    category: Optional[str]
    status: str                  # Registered / Not Registered / Found / Not Found / Error
    url: Optional[str]
    reason: Optional[str]
    extra: Optional[str]
    raw_line: Optional[str]
    confidence: float


def _scanner_bin() -> str:
    env_bin = os.getenv("USER_SCANNER_BIN", "").strip()
    if env_bin:
        return env_bin
    found = shutil.which("user-scanner")
    return found or "user-scanner"


def _timeout() -> int:
    try:
        return int(os.getenv("USER_SCANNER_TIMEOUT", "180"))
    except ValueError:
        return 180


def _normalize_status(value: str, scan_type: str) -> str:
    if not value:
        return "Error"
    v = value.strip().lower()
    if scan_type == "email":
        if v == "registered":
            return "Registered"
        if v == "not registered":
            return "Not Registered"
        return "Error"
    if v == "found":
        return "Found"
    if v == "not found":
        return "Not Found"
    return "Error"


def _confidence_from_status(status: str) -> float:
    s = status.lower()
    if s in {"registered", "found"}:
        return 0.92
    if s in {"not registered", "not found"}:
        return 0.85
    return 0.40


def _base_command(
    scan_type: str,
    target: str,
    category: Optional[str] = None,
    module: Optional[str] = None,
    proxy_file: Optional[str] = None,
    validate_proxies: bool = False,
    verbose: bool = True,
) -> List[str]:
    cmd = [_scanner_bin()]

    if verbose:
        cmd.append("-v")

    if scan_type == "email":
        cmd.extend(["-e", target])
    elif scan_type == "username":
        cmd.extend(["-u", target])
    else:
        raise ValueError(f"Unsupported scan_type: {scan_type}")

    if category:
        cmd.extend(["-c", category])
    if module:
        cmd.extend(["-m", module])
    if proxy_file:
        cmd.extend(["-P", proxy_file])
        if validate_proxies:
            cmd.append("--validate-proxies")

    return cmd


def _run_command(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=_timeout(),
        check=False,
    )


def _try_json_variants(
    scan_type: str,
    target: str,
    category: Optional[str],
    module: Optional[str],
    proxy_file: Optional[str],
    validate_proxies: bool,
) -> Optional[Dict[str, Any]]:
    """
    user-scanner заявляет JSON output, но формат ключей/флагов может меняться.
    Поэтому пробуем несколько типовых вариантов.
    """
    candidates = [
        ["--json"],
        ["--output", "json"],
        ["-o", "json"],
        ["--format", "json"],
    ]

    for tail in candidates:
        cmd = _base_command(
            scan_type=scan_type,
            target=target,
            category=category,
            module=module,
            proxy_file=proxy_file,
            validate_proxies=validate_proxies,
            verbose=True,
        ) + tail

        try:
            proc = _run_command(cmd)
        except Exception:
            continue

        stdout = (proc.stdout or "").strip()
        if proc.returncode != 0 and not stdout:
            continue

        parsed = _extract_json_from_text(stdout)
        if parsed is not None:
            return {
                "command": cmd,
                "stdout": stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
                "json": parsed,
            }

    return None


def _extract_json_from_text(text: str) -> Optional[Any]:
    text = (text or "").strip()
    if not text:
        return None

    # 1) Чистый JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2) Ищем JSON-массив/объект внутри stdout
    for opener, closer in [("{", "}"), ("[", "]")]:
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                continue

    return None


def _records_from_json(data: Any, scan_type: str, target: str) -> List[ScanRecord]:
    items: List[Dict[str, Any]] = []

    if isinstance(data, dict):
        if isinstance(data.get("results"), list):
            items = data["results"]
        else:
            items = [data]
    elif isinstance(data, list):
        items = data

    records: List[ScanRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        platform = (
            item.get("site_name")
            or item.get("platform")
            or item.get("site")
            or item.get("name")
            or "Unknown"
        )
        category = item.get("category")
        status = _normalize_status(item.get("status", ""), scan_type)
        url = item.get("url")
        reason = item.get("reason")
        extra = item.get("extra")

        records.append(
            ScanRecord(
                scan_type=scan_type,
                target=target,
                platform=str(platform),
                category=str(category) if category else None,
                status=status,
                url=str(url) if url else None,
                reason=str(reason) if reason else None,
                extra=str(extra) if extra else None,
                raw_line=None,
                confidence=_confidence_from_status(status),
            )
        )

    return records


LINE_RE = re.compile(
    r"""
    ^\s*
    \[(?P<mark>[^\]]+)\]\s*
    (?P<platform>.+?)
    (?:\s+\[(?P<url>https?://[^\]]+)\])?
    (?:\s+\((?P<target>[^)]+)\))?
    \s*:\s*
    (?P<status>Registered|Not\ Registered|Found|Not\ Found|Error)
    (?P<tail>.*?)
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _guess_category(platform: str) -> Optional[str]:
    p = platform.lower()
    if p in {"github", "gitlab", "bitbucket", "npm", "pypi", "huggingface", "replit"}:
        return "dev"
    if p in {"reddit", "instagram", "twitter", "x", "discord", "telegram", "facebook"}:
        return "social"
    if p in {"medium", "patreon", "hashnode", "dev.to", "substack"}:
        return "creator"
    return None


def _records_from_console(stdout: str, scan_type: str, target: str) -> List[ScanRecord]:
    records: List[ScanRecord] = []

    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue

        m = LINE_RE.match(line)
        if not m:
            continue

        platform = m.group("platform").strip()
        url = m.group("url")
        status = _normalize_status(m.group("status"), scan_type)
        tail = (m.group("tail") or "").strip(" -|:")
        reason = tail or None

        records.append(
            ScanRecord(
                scan_type=scan_type,
                target=target,
                platform=platform,
                category=_guess_category(platform),
                status=status,
                url=url,
                reason=reason,
                extra=None,
                raw_line=line,
                confidence=_confidence_from_status(status),
            )
        )

    return records


def _scan_one(
    scan_type: str,
    target: str,
    category: Optional[str] = None,
    module: Optional[str] = None,
    proxy_file: Optional[str] = None,
    validate_proxies: bool = False,
) -> Dict[str, Any]:
    json_probe = _try_json_variants(
        scan_type=scan_type,
        target=target,
        category=category,
        module=module,
        proxy_file=proxy_file,
        validate_proxies=validate_proxies,
    )

    if json_probe is not None:
        records = _records_from_json(json_probe["json"], scan_type=scan_type, target=target)
        return {
            "engine": "user-scanner",
            "mode": scan_type,
            "target": target,
            "records": [asdict(r) for r in records],
            "debug": {
                "parser": "json",
                "command": json_probe["command"],
                "returncode": json_probe["returncode"],
                "stderr": json_probe["stderr"],
            },
        }

    cmd = _base_command(
        scan_type=scan_type,
        target=target,
        category=category,
        module=module,
        proxy_file=proxy_file,
        validate_proxies=validate_proxies,
        verbose=True,
    )
    proc = _run_command(cmd)
    records = _records_from_console(proc.stdout or "", scan_type=scan_type, target=target)

    return {
        "engine": "user-scanner",
        "mode": scan_type,
        "target": target,
        "records": [asdict(r) for r in records],
        "debug": {
            "parser": "console",
            "command": cmd,
            "returncode": proc.returncode,
            "stderr": proc.stderr,
            "stdout_preview": (proc.stdout or "")[:3000],
        },
    }


def _summarize(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    found = [r for r in records if r["status"] in {"Found", "Registered"}]
    negative = [r for r in records if r["status"] in {"Not Found", "Not Registered"}]
    errors = [r for r in records if r["status"] == "Error"]

    by_category: Dict[str, int] = {}
    for r in records:
        cat = r.get("category") or "other"
        by_category[cat] = by_category.get(cat, 0) + 1

    return {
        "total": len(records),
        "positive": len(found),
        "negative": len(negative),
        "errors": len(errors),
        "by_category": by_category,
        "top_hits": found[:15],
    }


def analyze_profile(
    email: Optional[str] = None,
    username: Optional[str] = None,
    category: Optional[str] = None,
    module: Optional[str] = None,
    proxy_file: Optional[str] = None,
    validate_proxies: bool = False,
) -> Dict[str, Any]:
    scanner_path = _scanner_bin()

    if not shutil.which(scanner_path) and not os.path.exists(scanner_path):
        return {
            "ok": False,
            "engine": "user-scanner",
            "error": f"user-scanner not found: {scanner_path}",
            "email_results": [],
            "username_results": [],
            "summary": {
                "total": 0,
                "positive": 0,
                "negative": 0,
                "errors": 1,
                "by_category": {},
                "top_hits": [],
            },
            "notes": [
                "Установите user-scanner в виртуальное окружение.",
                "Проверьте USER_SCANNER_BIN в .env.",
            ],
        }

    email_records: List[Dict[str, Any]] = []
    username_records: List[Dict[str, Any]] = []
    debug: Dict[str, Any] = {}

    if email:
        email_scan = _scan_one(
            scan_type="email",
            target=email,
            category=category,
            module=module,
            proxy_file=proxy_file,
            validate_proxies=validate_proxies,
        )
        email_records = email_scan["records"]
        debug["email"] = email_scan["debug"]

    if username:
        username_scan = _scan_one(
            scan_type="username",
            target=username,
            category=category,
            module=module,
            proxy_file=proxy_file,
            validate_proxies=validate_proxies,
        )
        username_records = username_scan["records"]
        debug["username"] = username_scan["debug"]

    all_records = email_records + username_records
    summary = _summarize(all_records)

    notes: List[str] = []
    if email and not email_records:
        notes.append("По email не удалось извлечь структурированный результат. Проверьте stdout/stderr в debug.")
    if username and not username_records:
        notes.append("По username не удалось извлечь структурированный результат. Проверьте stdout/stderr в debug.")
    if summary["positive"] > 0:
        notes.append("Обнаружены реальные совпадения по открытым платформам.")
    if summary["errors"] > 0:
        notes.append("Часть платформ вернула ошибки или была недоступна из текущей сети.")

    return {
        "ok": True,
        "engine": "user-scanner",
        "email_results": email_records,
        "username_results": username_records,
        "summary": summary,
        "notes": notes,
        "debug": debug,
    }