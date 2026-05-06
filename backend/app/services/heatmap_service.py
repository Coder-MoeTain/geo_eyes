import json
from datetime import datetime

from app.db.crud import heatmap_points


def build_heatmap_feature_collection(db, start_date: datetime | None = None, end_date: datetime | None = None):
    rows = heatmap_points(db, start_date=start_date, end_date=end_date)
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(r.centroid_geojson),
                "properties": {"weight": r.confidence, "class_name": None, "confidence": r.confidence},
            }
            for r in rows
        ],
    }
