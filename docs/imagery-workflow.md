# Imagery Workflow

## Reliable Detection Path

1. Upload high-resolution GeoTIFF.
2. Validate CRS/metadata and georeference status.
3. Run YOLO detection job.
4. Store detections in PostGIS.
5. Render raster overlay via TiTiler.

## STAC Path

- STAC imagery from Sentinel-2/Landsat is marked as context-only.
- API returns explicit warning when imagery is insufficient for reliable aircraft detection.
