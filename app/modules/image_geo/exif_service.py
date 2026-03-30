import json
import math
import os
import shutil
import subprocess
from typing import Any, Dict, Optional, Tuple

import exifread


def _run_exiftool(path: str) -> Optional[Dict[str, Any]]:
    exiftool_bin = shutil.which("exiftool")
    if not exiftool_bin:
        return None

    try:
        proc = subprocess.run(
            [
                exiftool_bin,
                "-json",
                "-n",  # numeric values where possible
                "-GPSLatitude",
                "-GPSLongitude",
                "-GPSLatitudeRef",
                "-GPSLongitudeRef",
                "-DateTimeOriginal",
                "-CreateDate",
                "-ModifyDate",
                "-Make",
                "-Model",
                "-Software",
                "-ImageWidth",
                "-ImageHeight",
                "-Orientation",
                "-MIMEType",
                "-FileType",
                "-FileName",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

        if proc.returncode != 0 or not proc.stdout.strip():
            return None

        data = json.loads(proc.stdout)
        if not data or not isinstance(data, list):
            return None

        return data[0]
    except Exception:
        return None


def _ratio_to_float(value) -> float:
    try:
        return float(value.num) / float(value.den)
    except Exception:
        try:
            return float(value)
        except Exception:
            return 0.0


def _dms_to_decimal(values, ref: str) -> Optional[float]:
    try:
        d = _ratio_to_float(values[0])
        m = _ratio_to_float(values[1])
        s = _ratio_to_float(values[2])
        result = d + (m / 60.0) + (s / 3600.0)
        if ref in ("S", "W"):
            result *= -1
        return round(result, 7)
    except Exception:
        return None


def _run_exifread(path: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(f, details=False)

        make = tags.get("Image Make")
        model = tags.get("Image Model")
        dto = tags.get("EXIF DateTimeOriginal")
        software = tags.get("Image Software")

        result["Make"] = str(make) if make else None
        result["Model"] = str(model) if model else None
        result["DateTimeOriginal"] = str(dto) if dto else None
        result["Software"] = str(software) if software else None

        lat = tags.get("GPS GPSLatitude")
        lat_ref = tags.get("GPS GPSLatitudeRef")
        lon = tags.get("GPS GPSLongitude")
        lon_ref = tags.get("GPS GPSLongitudeRef")

        if lat and lat_ref and lon and lon_ref:
            lat_val = _dms_to_decimal(lat.values, str(lat_ref))
            lon_val = _dms_to_decimal(lon.values, str(lon_ref))
            result["GPSLatitude"] = lat_val
            result["GPSLongitude"] = lon_val

        return result
    except Exception:
        return result


def _normalize_exiftool(raw: Dict[str, Any]) -> Dict[str, Any]:
    lat = raw.get("GPSLatitude")
    lon = raw.get("GPSLongitude")

    normalized = {
        "source": "exiftool",
        "camera_make": raw.get("Make"),
        "camera_model": raw.get("Model"),
        "datetime_original": raw.get("DateTimeOriginal") or raw.get("CreateDate") or raw.get("ModifyDate"),
        "software": raw.get("Software"),
        "image_width": raw.get("ImageWidth"),
        "image_height": raw.get("ImageHeight"),
        "mime_type": raw.get("MIMEType"),
        "file_type": raw.get("FileType"),
        "orientation": raw.get("Orientation"),
        "gps": None,
        "raw": raw,
    }

    if lat is not None and lon is not None:
        try:
            normalized["gps"] = {
                "lat": round(float(lat), 7),
                "lon": round(float(lon), 7),
            }
        except Exception:
            pass

    return normalized


def _normalize_exifread(raw: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {
        "source": "exifread",
        "camera_make": raw.get("Make"),
        "camera_model": raw.get("Model"),
        "datetime_original": raw.get("DateTimeOriginal"),
        "software": raw.get("Software"),
        "image_width": None,
        "image_height": None,
        "mime_type": None,
        "file_type": None,
        "orientation": None,
        "gps": None,
        "raw": raw,
    }

    if raw.get("GPSLatitude") is not None and raw.get("GPSLongitude") is not None:
        normalized["gps"] = {
            "lat": raw["GPSLatitude"],
            "lon": raw["GPSLongitude"],
        }

    return normalized


def build_map_data(exif_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    gps = exif_data.get("gps")
    if not gps:
        return None

    lat = gps.get("lat")
    lon = gps.get("lon")
    if lat is None or lon is None:
        return None

    return {
        "lat": lat,
        "lon": lon,
        "zoom": 15,
        "popup": f"EXIF GPS: {lat}, {lon}",
    }


def extract_exif_full(path: str) -> Dict[str, Any]:
    raw_exiftool = _run_exiftool(path)
    if raw_exiftool:
        normalized = _normalize_exiftool(raw_exiftool)
    else:
        raw_exifread = _run_exifread(path)
        normalized = _normalize_exifread(raw_exifread)

    map_data = build_map_data(normalized)

    findings = []
    if normalized.get("camera_make") or normalized.get("camera_model"):
        findings.append("Обнаружены данные об устройстве съёмки.")
    if normalized.get("datetime_original"):
        findings.append("Обнаружена дата/время съёмки.")
    if normalized.get("gps"):
        findings.append("Обнаружены GPS-координаты в EXIF.")
    else:
        findings.append("GPS-координаты в EXIF не найдены.")

    return {
        "exif": normalized,
        "map_data": map_data,
        "findings": findings,
    }