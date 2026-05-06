import json
from sqlalchemy import text
from shapely.geometry import shape


def spatial_change_detection(db, before_image_id: int, after_image_id: int, match_distance_m: float):
    rows_before = db.execute(
        text(
            """
            SELECT id, class_name, confidence,
                   ST_AsGeoJSON(geo_polygon) AS poly,
                   ST_AsGeoJSON(centroid) AS cen
            FROM detections WHERE image_id=:id
            """
        ),
        {"id": before_image_id},
    ).mappings().all()
    rows_after = db.execute(
        text(
            """
            SELECT id, class_name, confidence,
                   ST_AsGeoJSON(geo_polygon) AS poly,
                   ST_AsGeoJSON(centroid) AS cen
            FROM detections WHERE image_id=:id
            """
        ),
        {"id": after_image_id},
    ).mappings().all()

    def iou(a, b):
        inter = a.intersection(b).area
        if inter <= 0:
            return 0.0
        return inter / max(1e-8, a.union(b).area)

    matched_before = set()
    matched_after = set()
    unchanged, moved, uncertain = [], [], []
    for i, a in enumerate(rows_after):
        if not a["poly"] or not a["cen"]:
            continue
        ga = shape(json.loads(a["poly"]))
        ca = shape(json.loads(a["cen"]))
        best = None
        for j, b in enumerate(rows_before):
            if j in matched_before or not b["poly"] or not b["cen"]:
                continue
            if a["class_name"] and b["class_name"] and a["class_name"] != b["class_name"]:
                continue
            gb = shape(json.loads(b["poly"]))
            cb = shape(json.loads(b["cen"]))
            dist_m = ca.distance(cb) * 111139.0
            if dist_m > match_distance_m:
                continue
            s = iou(ga, gb)
            conf_score = 1.0 - abs(float(a["confidence"] or 0) - float(b["confidence"] or 0))
            score = s * 0.7 + conf_score * 0.3
            if best is None or score > best[0]:
                best = (score, j, dist_m, s, cb)
        if best:
            _, j, dist_m, s, cb = best
            matched_after.add(i)
            matched_before.add(j)
            feature = {
                "type": "Feature",
                "geometry": json.loads(a["cen"]),
                "properties": {
                    "class_name": a["class_name"],
                    "confidence": a["confidence"],
                    "iou": s,
                    "movement_m": dist_m,
                    "movement_vector": [ca.x - cb.x, ca.y - cb.y],
                },
            }
            if s < 0.15:
                uncertain.append(feature)
            elif dist_m > max(5.0, match_distance_m * 0.25):
                moved.append(feature)
            else:
                unchanged.append(feature)

    new_rows = [{"type": "Feature", "geometry": json.loads(a["cen"]), "properties": {"class_name": a["class_name"], "confidence": a["confidence"]}} for i, a in enumerate(rows_after) if i not in matched_after and a["cen"]]
    removed_rows = [{"type": "Feature", "geometry": json.loads(b["cen"]), "properties": {"class_name": b["class_name"], "confidence": b["confidence"]}} for j, b in enumerate(rows_before) if j not in matched_before and b["cen"]]
    return {
        "new_aircraft": {"type": "FeatureCollection", "features": new_rows},
        "removed_aircraft": {"type": "FeatureCollection", "features": removed_rows},
        "moved_aircraft": {"type": "FeatureCollection", "features": moved},
        "unchanged_aircraft": {"type": "FeatureCollection", "features": unchanged},
        "uncertain": {"type": "FeatureCollection", "features": uncertain},
        "summary": {"new": len(new_rows), "removed": len(removed_rows), "moved": len(moved), "unchanged": len(unchanged), "uncertain": len(uncertain)},
    }
