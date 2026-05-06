from pathlib import Path

import rasterio
from rasterio.windows import Window


def tile_geotiff(input_path: str, output_dir: str, tile_size: int = 1024, overlap: int = 128):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with rasterio.open(input_path) as src:
        step = tile_size - overlap
        for y in range(0, src.height, step):
            for x in range(0, src.width, step):
                window = Window(x, y, min(tile_size, src.width - x), min(tile_size, src.height - y))
                transform = src.window_transform(window)
                profile = src.profile.copy()
                profile.update(
                    {
                        "height": window.height,
                        "width": window.width,
                        "transform": transform,
                    }
                )
                tile_file = out / f"tile_x{x}_y{y}.tif"
                with rasterio.open(tile_file, "w", **profile) as dst:
                    dst.write(src.read(window=window))


if __name__ == "__main__":
    tile_geotiff("data/sample/geotiff_sample.tif", "data/tiles")
