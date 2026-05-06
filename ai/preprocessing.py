import cv2
import numpy as np
import rasterio


def contrast_enhance(image: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l2 = clahe.apply(l)
    merged = cv2.merge((l2, a, b))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    return (nir - red) / (nir + red + 1e-6)


def preprocess_geotiff(input_tif: str, output_tif: str):
    with rasterio.open(input_tif) as src:
        data = src.read()
        profile = src.profile.copy()
    rgb = np.transpose(data[:3], (1, 2, 0)).astype(np.uint8)
    enhanced = contrast_enhance(rgb)
    out = np.transpose(enhanced, (2, 0, 1))
    with rasterio.open(output_tif, "w", **profile) as dst:
        dst.write(out)
