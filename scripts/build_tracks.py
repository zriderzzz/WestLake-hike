from pathlib import Path
import xml.etree.ElementTree as ET
import json
import re

ROOT = Path(__file__).resolve().parents[1]
TRACKS_DIR = ROOT / "tracks"
GEOJSON_PATH = ROOT / "tracks.geojson"
JSON_PATH = ROOT / "tracks.json"

def ns_uri(root):
    if root.tag.startswith("{"):
        return root.tag[1:].split("}")[0]
    return ""

def q(ns, tag):
    return f"{{{ns}}}{tag}" if ns else tag

def clean_title(path: Path, index: int):
    stem = path.stem
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}[-_ ]*", "", stem)
    stem = re.sub(r"[-_]+", " ", stem).strip()
    return stem or f"西湖群山徒步 {index:02d}"

def date_from_filename(path: Path):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    return m.group(1) if m else ""

def first_time(root, ns):
    for pt in root.findall(f".//{q(ns, 'trkpt')}"):
        t = pt.find(q(ns, "time"))
        if t is not None and t.text:
            return t.text.strip()
    return ""

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
        # Remove precise timestamps from newly uploaded GPX for public privacy.
        remove_precise_times(path)

        tree = ET.parse(path)
        root = tree.getroot()
        ns = ns_uri(root)

        date = date_from_filename(path)
        if not date:
            t = first_time(root, ns)
            date = t[:10] if t else ""

        # Prefer GPX track name, fallback to filename.
        trk_name = ""
        first_trk = root.find(q(ns, "trk"))
        if first_trk is not None:
            name_el = first_trk.find(q(ns, "name"))
            if name_el is not None and name_el.text:
                trk_name = name_el.text.strip()
        title = trk_name or clean_title(path, idx)

        total_points = 0
        segment_index = 0
        for trk in root.findall(q(ns, "trk")):
            for seg in trk.findall(q(ns, "trkseg")):
                coords = []
                for pt in seg.findall(q(ns, "trkpt")):
                    try:
                        lat = float(pt.attrib["lat"])
                        lon = float(pt.attrib["lon"])
                    except (KeyError, ValueError):
                        continue
                    coords.append([lon, lat])
                if not coords:
                    continue
                segment_index += 1
                total_points += len(coords)
                features.append({
                    "type": "Feature",
                    "properties": {
                        "id": idx,
                        "segment": segment_index,
                        "date": date,
                        "title": title,
                        "points": len(coords),
                        "visible": True,
                        "source": f"tracks/{path.name}"
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords
                    }
                })

        manifest.append({
            "id": idx,
            "date": date,
            "title": title,
            "file": f"tracks/{path.name}",
            "visible": True,
            "points": total_points
        })

    GEOJSON_PATH.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )
    JSON_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Generated {GEOJSON_PATH} from {len(gpx_files)} GPX files.")
    print(f"Generated {JSON_PATH}.")

if __name__ == "__main__":
    main()
