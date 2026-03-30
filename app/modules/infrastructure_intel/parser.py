import re
from typing import Any, Dict, List


REAL_IP_RE = re.compile(
    r"Real IP Address of\s+(?P<host>[^:]+):\s+(?P<ip>(?:\d{1,3}\.){3}\d{1,3})",
    re.IGNORECASE,
)

VISIBLE_IP_RE = re.compile(
    r"Visible IP Address:\s+(?P<ip>(?:\d{1,3}\.){3}\d{1,3})",
    re.IGNORECASE,
)

SUBDOMAIN_RE = re.compile(
    r"Subdomain Found\s+└➤\s+(?P<url>https?://\S+)",
    re.IGNORECASE,
)

SSL_COMMON_RE = re.compile(r"Common Name:\s+(?P<value>.+)", re.IGNORECASE)
SSL_ISSUER_RE = re.compile(r"Issuer:\s+(?P<value>.+)", re.IGNORECASE)
SSL_VALID_FROM_RE = re.compile(r"Validity Start:\s+(?P<value>.+)", re.IGNORECASE)
SSL_VALID_TO_RE = re.compile(r"Validity End:\s+(?P<value>.+)", re.IGNORECASE)


def parse_cloakquest_output(stdout: str) -> Dict[str, Any]:
    lines = [line.rstrip() for line in (stdout or "").splitlines() if line.strip()]

    origin_candidates: List[Dict[str, Any]] = []
    subdomain_signals: List[str] = []
    ssl_signals: List[str] = []
    history_signals: List[str] = []

    visible_ip = None
    current_origin = None

    for line in lines:
        m_visible = VISIBLE_IP_RE.search(line)
        if m_visible:
            visible_ip = m_visible.group("ip")

        m_sub = SUBDOMAIN_RE.search(line)
        if m_sub:
            subdomain_signals.append(m_sub.group("url"))

        if "Historical IP" in line or "SecurityTrails" in line or "history" in line.lower():
            history_signals.append(line)

        m_real = REAL_IP_RE.search(line)
        if m_real:
            current_origin = {
                "host": m_real.group("host").strip(),
                "ip": m_real.group("ip").strip(),
                "ssl_common_name": None,
                "ssl_issuer": None,
                "ssl_valid_from": None,
                "ssl_valid_to": None,
            }
            origin_candidates.append(current_origin)
            continue

        if current_origin:
            m = SSL_COMMON_RE.search(line)
            if m:
                current_origin["ssl_common_name"] = m.group("value").strip()
                ssl_signals.append(f"{current_origin['host']} → CN: {current_origin['ssl_common_name']}")
                continue

            m = SSL_ISSUER_RE.search(line)
            if m:
                current_origin["ssl_issuer"] = m.group("value").strip()
                ssl_signals.append(f"{current_origin['host']} → Issuer: {current_origin['ssl_issuer']}")
                continue

            m = SSL_VALID_FROM_RE.search(line)
            if m:
                current_origin["ssl_valid_from"] = m.group("value").strip()
                continue

            m = SSL_VALID_TO_RE.search(line)
            if m:
                current_origin["ssl_valid_to"] = m.group("value").strip()
                continue

    findings: List[str] = []

    if visible_ip:
        findings.append(f"Определён видимый IP домена: {visible_ip}.")

    if origin_candidates:
        findings.append(f"Обнаружены потенциальные origin IP: {len(origin_candidates)}.")
    else:
        findings.append("Потенциальные origin IP не выявлены по результатам текущего запуска.")

    if subdomain_signals:
        findings.append(f"Обнаружены поддомены: {len(subdomain_signals)}.")

    if ssl_signals:
        findings.append("Извлечены сигналы SSL/сертификатов для найденных узлов.")

    if history_signals:
        findings.append("Есть сообщения, связанные с историческими IP / внешними источниками данных.")

    return {
        "visible_ip": visible_ip,
        "origin_candidates": origin_candidates,
        "subdomain_signals": subdomain_signals[:50],
        "ssl_signals": ssl_signals[:50],
        "history_signals": history_signals[:50],
        "analytical_conclusion": findings,
        "raw_preview": lines[:120],
    }