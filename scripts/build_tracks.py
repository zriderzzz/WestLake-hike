from pathlib import Path
import xml.etree.ElementTree as ET
import json
import math
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
TRACKS_DIR = ROOT / "tracks"
GEOJSON_PATH = ROOT / "tracks.geojson"
JSON_PATH = ROOT / "tracks.json"
ELEVATION_GAIN_THRESHOLD = 2.0


def ns_uri(root):
    if root.tag.startswith("{"):
        return root.tag[1:].split("}")[0]
    return ""


def q(ns, tag):
    return f"{{{ns}}}{tag}" if ns else tag


def clean_title(path: Path, index: int):
    stem = unquote(path.stem)
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}[-_ ]*", "", stem)
    stem = re.sub(r"[-_]+", " ", stem).strip()
    return stem or f"西湖群山徒步 {index:02d}"


def clean_name(text):
    return unquote(text or "").strip()


def date_from_filename(path: Path):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    return m.group(1) if m else ""


def first_time(root, ns):
    for pt in root.findall(f".//{q(ns, 'trkpt')}"):
        t = pt.find(q(ns, "time"))
        if t is not None and t.text:
            return t.text.strip()
    return ""


def point_elevation(pt, ns):
    ele = pt.find(q(ns, "ele"))
    if ele is None or ele.text is None:
        return None
    try:
        return float(ele.text)
    except ValueError:
        return None


def haversine_distance(a, b):
    radius = 6371000
    lat1 = math.radians(a[0])
    lat2 = math.radians(b[0])
    d_lat = math.radians(b[0] - a[0])
    d_lon = math.radians(b[1] - a[1])

    x = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    )
    return 2 * radius * math.atan2(math.sqrt(x), math.sqrt(1 - x))


def rounded(value, digits=1):
    return round(value, digits) if value is not None else None


def update_elevation_stats(stats, elevation):
    if elevation is None:
        return
    stats["min_elevation"] = elevation if stats["min_elevation"] is None else min(stats["min_elevation"], elevation)
    stats["max_elevation"] = elevation if stats["max_elevation"] is None else max(stats["max_elevation"], elevation)


def remove_precise_times(gpx_path: Path):
    """Remove trackpoint time nodes in-place for privacy, preserve coordinates and route shape."""
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    ns = ns_uri(root)
    changed = False
    for parent in root.iter():
        for child in list(parent):
            if child.tag == q(ns, "time"):
                parent.remove(child)
                changed = True
    if changed:
        ET.register_namespace("", ns or "http://www.topografix.com/GPX/1/1")
        tree.write(gpx_path, encoding="utf-8", xml_declaration=True)


def main():
    if not TRACKS_DIR.exists():
        raise SystemExit("tracks/ directory not found")

    gpx_files = sorted(TRACKS_DIR.glob("*.gpx"), key=lambda p: p.name)
    features = []
    manifest = []

    for idx, path in enumerate(gpx_files, start=1):
        tree = ET.parse(path)
        root = tree.getroot()
        ns = ns_uri(root)

        date = date_from_filename(path)
        if not date:
            t = first_time(root, ns)
            date = t[:10] if t else ""

        trk_name = ""
        first_trk = root.find(q(ns, "trk"))
        if first_trk is not None:
            name_el = first_trk.find(q(ns, "name"))
            if name_el is not None and name_el.text:
                trk_name = clean_name(name_el.text)
        title = trk_name or clean_title(path, idx)

        track_stats = {
            "points": 0,
            "distance": 0.0,
            "ascent": 0.0,
            "descent": 0.0,
            "min_elevation": None,
            "max_elevation": None,
        }

        segment_index = 0
        for trk in root.findall(q(ns, "trk")):
            for seg in trk.findall(q(ns, "trkseg")):
                coords = []
                segment_stats = {
                    "points": 0,
                    "distance": 0.0,
                    "ascent": 0.0,
                    "descent": 0.0,
                    "min_elevation": None,
                    "max_elevation": None,
                }
                last_latlon = None
                last_elevation = None

                for pt in seg.findall(q(ns, "trkpt")):
                    try:
                        lat = float(pt.attrib["lat"])
                        lon = float(pt.attrib["lon"])
                    except (KeyError, ValueError):
                        continue

                    elevation = point_elevation(pt, ns)
                    coord = [round(lon, 7), round(lat, 7)]
                    if elevation is not None:
                        coord.append(round(elevation, 1))

                    if last_latlon is not None:
                        distance = haversine_distance(last_latlon, [lat, lon])
                        segment_stats["distance"] += distance
                        track_stats["distance"] += distance

                    if elevation is not None and last_elevation is not None:
                        delta = elevation - last_elevation
                        if delta >= ELEVATION_GAIN_THRESHOLD:
                            segment_stats["ascent"] += delta
                            track_stats["ascent"] += delta
                        elif delta <= -ELEVATION_GAIN_THRESHOLD:
                            segment_stats["descent"] += abs(delta)
                            track_stats["descent"] += abs(delta)

                    update_elevation_stats(segment_stats, elevation)
                    update_elevation_stats(track_stats, elevation)
                    coords.append(coord)
                    segment_stats["points"] += 1
                    track_stats["points"] += 1
                    last_latlon = [lat, lon]
                    if elevation is not None:
                        last_elevation = elevation

                if not coords:
                    continue

                segment_index += 1
                features.append({
                    "type": "Feature",
                    "properties": {
                        "id": idx,
                        "segment": segment_index,
                        "date": date,
                        "title": title,
                        "points": segment_stats["points"],
                        "distance": rounded(segment_stats["distance"]),
                        "ascent": rounded(segment_stats["ascent"]),
                        "descent": rounded(segment_stats["descent"]),
                        "min_elevation": rounded(segment_stats["min_elevation"]),
                        "max_elevation": rounded(segment_stats["max_elevation"]),
                        "visible": True,
                        "source": f"tracks/{path.name}",
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords,
                    },
                })

        manifest.append({
            "id": idx,
            "date": date,
            "title": title,
            "file": f"tracks/{path.name}",
            "visible": True,
            "points": track_stats["points"],
            "distance": rounded(track_stats["distance"]),
            "ascent": rounded(track_stats["ascent"]),
            "descent": rounded(track_stats["descent"]),
            "min_elevation": rounded(track_stats["min_elevation"]),
            "max_elevation": rounded(track_stats["max_elevation"]),
        })

        # Remove precise timestamps from newly uploaded GPX for public privacy.
        remove_precise_times(path)

    GEOJSON_PATH.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    JSON_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Generated {GEOJSON_PATH} from {len(gpx_files)} GPX files.")
    print(f"Generated {JSON_PATH}.")


if __name__ == "__main__":
    main()
