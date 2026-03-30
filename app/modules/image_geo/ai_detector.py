def detect_synthetic_risk(ela_score: float, exif_payload: dict, yandex_match_count: int):
    score = 0; reasons = []
    if not exif_payload or not any(exif_payload.values()):
        score += 25; reasons.append("Отсутствуют или вырезаны метаданные EXIF")
    if ela_score < 1.2:
        score += 30; reasons.append("Низкий ELA score: возможна синтетичность или сильная пересохранённость")
    elif ela_score < 2.0:
        score += 15; reasons.append("Умеренно низкий ELA score")
    if yandex_match_count == 0:
        score += 10; reasons.append("Публичные интернет-дубликаты не обнаружены")
    verdict = "low"
    if score >= 55: verdict = "high"
    elif score >= 30: verdict = "medium"
    return {"score": min(score, 100), "risk": verdict, "reasons": reasons}
