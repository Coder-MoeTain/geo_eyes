import argparse
import csv
from pathlib import Path

from geoalchemy2.elements import WKTElement

from app.db.session import SessionLocal
from app.models import Airport


def import_airports(csv_path: Path):
    db = SessionLocal()
    inserted = 0
    try:
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("type") not in {"small_airport", "medium_airport", "large_airport"}:
                    continue
                icao = (row.get("ident") or "").strip()
                if not icao:
                    icao = None
                lat = row.get("latitude_deg")
                lon = row.get("longitude_deg")
                try:
                    latf = float(lat or "")
                    lonf = float(lon or "")
                except ValueError:
                    continue
                if icao:
                    exists = db.query(Airport).filter(Airport.icao_code == icao).one_or_none()
                    if exists:
                        continue
                db.add(
                    Airport(
                        ident=icao,
                        icao_code=icao,
                        iata_code=(row.get("iata_code") or "").strip() or None,
                        municipality=(row.get("municipality") or "").strip() or None,
                        name=(row.get("name") or icao).strip(),
                        country=(row.get("iso_country") or "").strip() or None,
                        type=(row.get("type") or "").strip() or None,
                        geom=WKTElement(f"POINT({lonf} {latf})", srid=4326),
                    )
                )
                inserted += 1
        db.commit()
    finally:
        db.close()
    print({"inserted": inserted})


def main():
    parser = argparse.ArgumentParser(description="Import OurAirports CSV into PostGIS airports table")
    parser.add_argument("--csv", required=True, help="Path to airports.csv from OurAirports")
    args = parser.parse_args()
    import_airports(Path(args.csv).resolve())


if __name__ == "__main__":
    main()
