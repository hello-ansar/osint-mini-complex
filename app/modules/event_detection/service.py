from collections import defaultdict
from pathlib import Path
import json

EVENT_KEYWORDS = {
    "protest": ["protest", "demonstration", "rally", "crowd", "march", "митинг", "акция", "скопление", "протест", "толпа"],
    "conflict": ["attack", "clash", "explosion", "gunfire", "strike", "обстрел", "столкновение", "взрыв", "стрельба"],
    "emergency": ["fire", "flood", "earthquake", "evacuation", "collapse", "пожар", "эвакуация", "возгорание", "обрушение"],
    "security": ["checkpoint", "security", "detention", "raid", "blockpost", "проверка", "блокпост", "досмотр", "задержание"],
    "infrastructure": ["power outage", "substation", "bridge", "pipeline", "telecom", "подстанция", "отключение", "электроснабжение", "авария"],
}
SEVERITY_WORDS = {
    "high": ["killed", "injured", "explosion", "gunfire", "evacuation", "casualties", "пострадал", "взрыв", "эвакуация"],
    "medium": ["blocked", "crowd", "detention", "fire", "outage", "closure", "перекрытие", "скопление", "задержка", "проверка"],
}

def load_demo_posts():
    return json.loads(Path("data/events/demo_posts.json").read_text(encoding="utf-8"))

def detect_type(text: str):
    text_l = text.lower(); scores = {}
    for event_type, words in EVENT_KEYWORDS.items():
        count = sum(1 for w in words if w in text_l)
        if count:
            scores[event_type] = count
    if not scores:
        return "other", 0.35
    best_type = max(scores, key=scores.get)
    confidence = min(0.55 + scores[best_type] * 0.12, 0.95)
    return best_type, round(confidence, 2)

def estimate_severity(text: str, source_count: int):
    text_l = text.lower()
    high = sum(1 for w in SEVERITY_WORDS["high"] if w in text_l)
    med = sum(1 for w in SEVERITY_WORDS["medium"] if w in text_l)
    score = high * 2 + med + max(source_count - 1, 0)
    if score >= 4: return "high"
    if score >= 2: return "medium"
    return "low"

def cluster_posts(posts):
    groups = defaultdict(list)
    for p in posts:
        event_type, confidence = detect_type(p["text"])
        p["event_type"] = event_type; p["confidence"] = confidence
        groups[(event_type, p["location"])].append(p)
    events = []
    for i, ((event_type, location), items) in enumerate(groups.items(), start=1):
        items = sorted(items, key=lambda x: x["published_at"], reverse=True)
        source_count = len({x["source"] for x in items})
        severity = estimate_severity(" ".join(x["text"] for x in items), source_count)
        avg_conf = round(sum(x["confidence"] for x in items) / len(items), 2)
        events.append({
            "event_id": f"EV-{i:03d}",
            "title": items[0]["headline"],
            "event_type": event_type,
            "location": location,
            "published_at": items[0]["published_at"],
            "severity": severity,
            "confidence": avg_conf,
            "source_count": source_count,
            "post_count": len(items),
            "summary": items[0]["text"][:220] + ("..." if len(items[0]["text"]) > 220 else ""),
            "posts": items,
        })
    severity_rank = {"high": 3, "medium": 2, "low": 1}
    return sorted(events, key=lambda x: (severity_rank.get(x["severity"], 0), x["published_at"]), reverse=True)

def get_dashboard_stats(events):
    return {
        "total_events": len(events),
        "high_severity": sum(1 for e in events if e["severity"] == "high"),
        "sources": len({p["source"] for e in events for p in e["posts"]}),
        "avg_confidence": round(sum(e["confidence"] for e in events) / len(events), 2) if events else 0,
    }

def get_event_payload():
    events = cluster_posts(load_demo_posts())
    return {"stats": get_dashboard_stats(events), "events": events}
