import os
import shutil
import subprocess
from typing import Any, Dict, Optional

from .parser import parse_cloakquest_output

DEFAULT_TIMEOUT = 120


def analyze_infrastructure(domain: str, tool_path: Optional[str] = None) -> Dict[str, Any]:
    domain = (domain or "").strip()

    if not domain:
        return {
            "ok": False,
            "error": "Не указан домен.",
            "analytical_conclusion": ["Запрос отклонён: домен не передан."],
        }

    resolved_tool = tool_path or os.getenv("CLOAKQUEST3R_PATH", "").strip()

    if not resolved_tool:
        return {
            "ok": False,
            "error": "Не указан путь к CloakQuest3r.",
            "analytical_conclusion": [
                "Не задан путь к скрипту CloakQuest3r.",
                "Укажи CLOAKQUEST3R_PATH в .env или передай tool_path в запросе.",
            ],
        }

    if not os.path.exists(resolved_tool):
        return {
            "ok": False,
            "error": f"Файл инструмента не найден: {resolved_tool}",
            "analytical_conclusion": [
                "Скрипт CloakQuest3r не найден по указанному пути."
            ],
        }

    python_bin = os.getenv("CLOAKQUEST3R_PYTHON", "").strip() or shutil.which("python3") or "python3"
    timeout_sec = int(os.getenv("CLOAKQUEST3R_TIMEOUT", DEFAULT_TIMEOUT))

    cmd = [python_bin, resolved_tool, domain]

    # Ответы на интерактивные вопросы:
    # 1. proceed? -> yes
    # 2. custom wordlist? -> no
    scripted_input = "yes\nno\n"

    try:
        proc = subprocess.run(
            cmd,
            input=scripted_input,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout if isinstance(e.stdout, str) else (
            e.stdout.decode(errors="ignore") if e.stdout else ""
        )
        stderr = e.stderr if isinstance(e.stderr, str) else (
            e.stderr.decode(errors="ignore") if e.stderr else ""
        )

        parsed = parse_cloakquest_output(stdout)

        return {
            "ok": True,
            "domain": domain,
            "engine": "CloakQuest3r",
            "returncode": 124,
            "timed_out": True,
            "command": cmd,
            "stdout_preview": stdout[:5000],
            "stderr_preview": stderr[:2000],
            **parsed,
            "analytical_conclusion": parsed["analytical_conclusion"] + [
                "Сканирование было ограничено по времени. Показаны частичные результаты."
            ],
        }
    except Exception as e:
        return {
            "ok": False,
            "error": repr(e),
            "analytical_conclusion": ["Ошибка запуска инфраструктурного анализа."],
        }

    parsed = parse_cloakquest_output(proc.stdout or "")

    severity = "medium" if parsed["origin_candidates"] else "low"

    return {
        "ok": True,
        "domain": domain,
        "engine": "CloakQuest3r",
        "returncode": proc.returncode,
        "timed_out": False,
        "command": cmd,
        "severity": severity,
        "stdout_preview": (proc.stdout or "")[:5000],
        "stderr_preview": (proc.stderr or "")[:2000],
        **parsed,
    }