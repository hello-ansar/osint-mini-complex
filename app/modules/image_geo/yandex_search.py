import os
import base64
import requests

DEFAULT_YANDEX_URL = "https://searchapi.api.cloud.yandex.net/v2/image/search_by_image"


def search_image_yandex(file_bytes: bytes):
    enabled = os.getenv("YANDEX_SEARCH_ENABLED", "false").lower() == "true"
    api_key = os.getenv("YANDEX_API_KEY", "").strip()
    folder_id = os.getenv("YANDEX_FOLDER_ID", "").strip()
    endpoint = os.getenv("YANDEX_SEARCH_URL", DEFAULT_YANDEX_URL).strip()

    if not enabled:
        return {
            "enabled": False,
            "results": [],
            "error": "disabled",
            "endpoint": endpoint,
        }

    if not api_key or not folder_id:
        return {
            "enabled": True,
            "results": [],
            "error": "missing_env",
            "endpoint": endpoint,
        }

    if len(file_bytes) > 3145728:
        return {
            "enabled": True,
            "results": [],
            "error": "image_too_large",
            "endpoint": endpoint,
        }

    try:
        payload = {
            "folderId": folder_id,
            "data": base64.b64encode(file_bytes).decode("utf-8"),
            "page": 0,
        }

        headers = {
            "Authorization": f"Api-Key {api_key}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=60,
        )

        debug_preview = response.text[:1500]

        if response.status_code != 200:
            return {
                "enabled": True,
                "results": [],
                "error": f"http_{response.status_code}",
                "endpoint": endpoint,
                "debug": debug_preview,
            }

        data = response.json()

        results = []
        for img in data.get("images", []):
            results.append({
                "title": img.get("pageTitle") or "",
                "url": img.get("url") or "",
                "host": img.get("host") or "",
                "page_url": img.get("pageUrl") or "",
                "passage": img.get("passage") or "",
                "width": img.get("width"),
                "height": img.get("height"),
            })

        return {
            "enabled": True,
            "results": results,
            "error": None,
            "endpoint": endpoint,
            "cbir_id": data.get("id"),
            "page": data.get("page"),
        }

    except Exception as e:
        return {
            "enabled": True,
            "results": [],
            "error": repr(e),
            "endpoint": endpoint,
        }