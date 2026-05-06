# Geospatial Correctness

- Never store pixel coordinates as EPSG:4326 geometries.
- For JPG/PNG and non-georeferenced rasters: store `pixel_bbox` only.
- For georeferenced GeoTIFF: transform detection polygons to WGS84 before PostGIS insert.
- Invalid CRS inputs are rejected for geospatial workflows.
- Geometry validation/repair is required before persistence.
