from PIL import Image, ExifTags

def _to_float(x):
    try:
        return float(x)
    except Exception:
        try:
            return float(x.numerator) / float(x.denominator)
        except Exception:
            return None

def _convert_gps(value):
    try:
        d = _to_float(value[0]); m = _to_float(value[1]); s = _to_float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None

def extract_exif(pil_image: Image.Image):
    try:
        raw = pil_image.getexif()
        if not raw: return {}
        exif, gps_raw = {}, {}
        for tag_id, value in raw.items():
            tag = ExifTags.TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                for gps_id, gps_val in value.items():
                    gps_raw[ExifTags.GPSTAGS.get(gps_id, gps_id)] = gps_val
            else:
                exif[tag] = value
        gps = None
        if gps_raw:
            lat = _convert_gps(gps_raw.get("GPSLatitude", []))
            lon = _convert_gps(gps_raw.get("GPSLongitude", []))
            if lat is not None and lon is not None:
                if gps_raw.get("GPSLatitudeRef") == "S": lat *= -1
                if gps_raw.get("GPSLongitudeRef") == "W": lon *= -1
                gps = {"lat": round(lat, 6), "lon": round(lon, 6)}
        return {
            "camera_make": str(exif.get("Make", "")) or None,
            "camera_model": str(exif.get("Model", "")) or None,
            "datetime_original": str(exif.get("DateTimeOriginal", "")) or None,
            "gps": gps,
        }
    except Exception:
        return {}
