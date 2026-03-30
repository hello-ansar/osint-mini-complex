from pathlib import Path
import tempfile
import json
from collections import Counter
from PIL import Image
import imagehash
from pillow_heif import register_heif_opener
from PIL import Image, UnidentifiedImageError

register_heif_opener()

from .ela import compute_ela_score
from .ai_detector import detect_synthetic_risk
from .yandex_search import search_image_yandex
from .exif_service import extract_exif_full

INDEX_PATH = Path("data/image_index/demo_index.json")


def load_demo_index():
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def hamming_similarity(hash_a: str, hash_b: str) -> int:
    try:
        dist = imagehash.hex_to_hash(hash_a) - imagehash.hex_to_hash(hash_b)
        return max(0, int(round((1 - dist / 64) * 100)))
    except Exception:
        return 0


def local_reverse_search(phash_hex: str):
    results = []
    for item in load_demo_index():
        sim = hamming_similarity(phash_hex, item["phash"])
        results.append({
            "title": item["title"],
            "image_url": item["image_url"],
            "page_url": item["page_url"],
            "host": item["host"],
            "passage": item["passage"],
            "source": "Local demo index",
            "similarity": sim,
            "location_hint": item.get("location_hint"),
        })
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:5]


def infer_location(exif_payload, local_matches, yandex_matches):
    if exif_payload.get("gps"):
        gps = exif_payload["gps"]
        return {
            "method": "EXIF GPS",
            "label": f"{gps['lat']}, {gps['lon']}",
            "confidence": 0.96,
        }

    hint_counter = Counter()

    for item in local_matches[:3]:
        if item.get("location_hint"):
            hint_counter[item["location_hint"]] += item["similarity"]

    for item in yandex_matches[:5]:
        joined = " ".join([
            str(item.get("title") or ""),
            str(item.get("passage") or ""),
            str(item.get("host") or "")
        ]).lower()

        for clue in ["tashkent", "samarkand", "andijan", "astana", "almaty", "uzbekistan", "kazakhstan"]:
            if clue in joined:
                hint_counter[clue.title()] += 35

    if not hint_counter:
        return {
            "method": "Indirect visual inference",
            "label": "Недостаточно данных для уверенной геопривязки",
            "confidence": 0.34,
        }

    label, value = hint_counter.most_common(1)[0]
    return {
        "method": "Indirect visual inference",
        "label": label,
        "confidence": round(min(0.45 + value / 150.0, 0.88), 2),
    }


def build_conclusion(exif_payload, local_matches, yandex_bundle, ela_score, ai_risk):
    points = []

    points.append(
        "GPS-координаты обнаружены в EXIF. Возможна прямая геопривязка."
        if exif_payload.get("gps")
        else "GPS-координаты отсутствуют. Выполнен переход к косвенным методам анализа изображения."
    )

    points.append(
        f"В EXIF найдено время съёмки: {exif_payload['datetime_original']}."
        if exif_payload.get("datetime_original")
        else "Дата/время съёмки в EXIF не найдены или были удалены при пересохранении."
    )

    if yandex_bundle.get("results"):
        points.append(f"Через Yandex Search API обнаружено интернет-совпадений: {len(yandex_bundle['results'])}.")
    else:
        err = yandex_bundle.get("error")
        points.append(
            "Интернет-поиск дубликатов отключён, используется локальный индекс."
            if err == "disabled"
            else f"Внешний интернет-поиск недоступен ({err}), используется локальный индекс."
            if err
            else "Публичные интернет-дубликаты не найдены по первой странице выдачи."
        )

    if local_matches:
        best = local_matches[0]
        points.append(f"Лучшее локальное визуальное совпадение: {best['title']} ({best['similarity']}%).")

    points.append(f"ELA score: {ela_score}.")
    points.append(f"Риск синтетичности / ИИ-генерации: {ai_risk['risk']} ({ai_risk['score']}%).")

    return points


def analyze_image_bytes(file_bytes: bytes, filename: str):
    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix or ".jpg", delete=False) as tmp:
        tmp.write(file_bytes)
        temp_path = tmp.name

    img = Image.open(temp_path).convert("RGB")

    exif_result = extract_exif_full(temp_path)
    exif_payload = exif_result["exif"]
    map_data = exif_result["map_data"]

    ph, dh = str(imagehash.phash(img)), str(imagehash.dhash(img))
    local_matches = local_reverse_search(ph)
    yandex_bundle = search_image_yandex(file_bytes)
    yandex_results = yandex_bundle.get("results", [])
    ela_score = compute_ela_score(temp_path)
    ai_risk = detect_synthetic_risk(ela_score, exif_payload, len(yandex_results))
    location = infer_location(exif_payload, local_matches, yandex_results)

    try:
        img = Image.open(temp_path).convert("RGB")
    except UnidentifiedImageError:
        return {
            "file_name": filename,
            "error": "Сервер не смог распознать изображение. Поддерживаются JPG, PNG, WebP, а для HEIC нужна библиотека pillow-heif.",
            "exif": {},
            "map_data": None,
            "hashes": {},
            "ela_score": None,
            "synthetic_risk": {"risk": "unknown", "score": 0},
            "location_assessment": {
                "method": "n/a",
                "label": "Анализ не выполнен",
                "confidence": 0
            },
            "reverse_search": {"yandex": {"results": [], "error": "image_open_failed"}, "local_matches": []},
            "analytical_conclusion": [
                "Файл не удалось открыть как изображение.",
                "Если это HEIC с iPhone, установите pillow-heif или конвертируйте файл в JPG."
            ],
        }

    return {
        "file_name": filename,
        "exif": exif_payload,
        "map_data": map_data,
        "hashes": {"phash": ph, "dhash": dh},
        "ela_score": ela_score,
        "synthetic_risk": ai_risk,
        "location_assessment": location,
        "reverse_search": {
            "yandex": yandex_bundle,
            "local_matches": local_matches,
        },
        "analytical_conclusion": build_conclusion(
            exif_payload,
            local_matches,
            yandex_bundle,
            ela_score,
            ai_risk,
        ),
    }