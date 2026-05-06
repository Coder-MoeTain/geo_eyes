from collections import Counter
from datetime import datetime

from geoalchemy2.elements import WKTElement
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AIModel, AircraftClass, Airport, Detection, SatelliteImage


def get_or_create_aircraft_class(db: Session, name: str) -> AircraftClass:
    item = db.query(AircraftClass).filter(AircraftClass.name == name).one_or_none()
    if item:
        return item
    item = AircraftClass(name=name, description=name)
    db.add(item)
    db.flush()
    return item


def create_satellite_image(
    db: Session,
    provider: str,
    acquisition_date: datetime,
    cloud_cover: float,
    resolution_m: float,
    bounds_wkt: str | None,
    asset_url: str | None,
    metadata: dict,
) -> SatelliteImage:
    record = SatelliteImage(
        provider=provider,
        acquisition_date=acquisition_date,
        cloud_cover=cloud_cover,
        resolution_m=resolution_m,
        footprint=WKTElement(bounds_wkt, srid=4326) if bounds_wkt else None,
        asset_url=asset_url,
        extra_metadata=metadata,
    )
    db.add(record)
    db.flush()
    return record


def create_detection(
    db: Session,
    image_id: int | None,
    model_id: int | None,
    class_name: str,
    confidence: float,
    pixel_bbox: dict,
    polygon_wkt: str | None,
    centroid_wkt: str | None,
    georeferenced: bool,
    timestamp: datetime,
    attributes: dict,
) -> Detection:
    klass = get_or_create_aircraft_class(db, class_name)
    item = Detection(
        image_id=image_id,
        model_id=model_id,
        class_id=klass.id,
        class_name=class_name,
        confidence=confidence,
        pixel_bbox=pixel_bbox,
        bbox_polygon=WKTElement(polygon_wkt, srid=4326) if polygon_wkt else None,
        centroid=WKTElement(centroid_wkt, srid=4326) if centroid_wkt else None,
        georeferenced=georeferenced,
        timestamp=timestamp,
        attributes=attributes,
    )
    db.add(item)
    db.flush()
    return item


def list_detections(db: Session, limit: int):
    rows = (
        db.query(
            Detection.id,
            Detection.confidence,
            Detection.timestamp,
            AircraftClass.name.label("class_name"),
            func.ST_AsGeoJSON(Detection.bbox_polygon).label("bbox_geojson"),
        )
        .join(AircraftClass, Detection.class_id == AircraftClass.id, isouter=True)
        .order_by(Detection.timestamp.desc())
        .limit(limit)
        .all()
    )
    return rows


def compute_aircraft_statistics(db: Session):
    rows = db.query(AircraftClass.name, Detection.confidence).join(
        Detection, Detection.class_id == AircraftClass.id, isouter=False
    )
    by_class = Counter()
    scores = []
    for klass, conf in rows:
        by_class[klass] += 1
        scores.append(conf)
    total = sum(by_class.values())
    return {
        "total_aircraft": total,
        "by_class": dict(by_class),
        "avg_confidence": round(sum(scores) / len(scores), 3) if scores else 0.0,
    }


def heatmap_points(db: Session, start_date: datetime | None = None, end_date: datetime | None = None):
    q = db.query(
        Detection.id,
        Detection.confidence,
        Detection.timestamp,
        func.ST_AsGeoJSON(Detection.centroid).label("centroid_geojson"),
    )
    if start_date:
        q = q.filter(Detection.timestamp >= start_date)
    if end_date:
        q = q.filter(Detection.timestamp <= end_date)
    return q.all()


def create_ai_model(db: Session, name: str, version: str, weights_path: str, metrics: dict, active: bool) -> AIModel:
    if active:
        db.query(AIModel).update({"active": False})
    row = AIModel(
        name=name,
        version=version,
        weights_path=weights_path,
        metrics=metrics,
        active=active,
    )
    db.add(row)
    db.flush()
    return row


def set_active_model(db: Session, model_id: int) -> AIModel | None:
    row = db.query(AIModel).filter(AIModel.id == model_id).one_or_none()
    if not row:
        return None
    db.query(AIModel).update({"active": False})
    row.active = True
    db.add(row)
    db.flush()
    return row


def get_active_model(db: Session) -> AIModel | None:
    return db.query(AIModel).filter(AIModel.active.is_(True)).order_by(AIModel.created_at.desc()).first()


def nearby_airports(db: Session, latitude: float, longitude: float, radius_km: float = 50.0, limit: int = 50):
    radius_m = radius_km * 1000.0
    point = f"SRID=4326;POINT({longitude} {latitude})"
    return (
        db.query(
            Airport.id,
            Airport.name,
            Airport.icao_code,
            Airport.iata_code,
            Airport.country,
            func.ST_AsGeoJSON(Airport.geom).label("geometry"),
            func.ST_DistanceSphere(Airport.geom, WKTElement(point, srid=4326)).label("distance_m"),
        )
        .filter(
            func.ST_DWithin(
                func.Geography(Airport.geom),
                func.Geography(WKTElement(point, srid=4326)),
                radius_m,
            )
        )
        .order_by("distance_m")
        .limit(limit)
        .all()
    )
