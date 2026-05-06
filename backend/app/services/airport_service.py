import csv
from pathlib import Path

from geoalchemy2.elements import WKTElement
from sqlalchemy import text

from app.models import Airport


def import_ourairports_csv(db, csv_path: str) -> int:
    inserted = 0
    with Path(csv_path).open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ident = (row.get("ident") or "").strip()
            if not ident:
                continue
            try:
                lat = float(row.get("latitude_deg") or "")
                lon = float(row.get("longitude_deg") or "")
            except ValueError:
                continue
            if db.query(Airport).filter(Airport.ident == ident).one_or_none():
                continue
            db.add(
                Airport(
                    ident=ident,
                    icao_code=ident[:8],
                    iata_code=(row.get("iata_code") or "").strip() or None,
                    municipality=(row.get("municipality") or "").strip() or None,
                    country=(row.get("iso_country") or "").strip() or None,
                    type=(row.get("type") or "").strip() or None,
                    name=(row.get("name") or ident).strip(),
                    geom=WKTElement(f"POINT({lon} {lat})", srid=4326),
                )
            )
            inserted += 1
    db.commit()
    return inserted


def search_airports(db, q: str, limit: int = 25):
    return db.execute(
        text(
            """
            SELECT id, ident, name, iata_code, municipality, country, type, ST_AsGeoJSON(geom) AS geometry
            FROM airports
            WHERE lower(name) LIKE :q OR lower(ident) LIKE :q OR lower(coalesce(iata_code,'')) LIKE :q
            ORDER BY name
            LIMIT :limit
            """
        ),
        {"q": f"%{q.lower()}%", "limit": limit},
    ).mappings().all()
