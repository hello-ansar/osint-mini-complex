from pathlib import Path
import tempfile
import cv2
import numpy as np

def compute_ela_score(image_path: str) -> float:
    try:
        original = cv2.imread(image_path)
        if original is None: return 0.0
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            temp_path = tmp.name
        cv2.imwrite(temp_path, original, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        compressed = cv2.imread(temp_path)
        diff = cv2.absdiff(original, compressed)
        score = float(np.mean(diff))
        Path(temp_path).unlink(missing_ok=True)
        return round(score, 3)
    except Exception:
        return 0.0
