import numpy as np
from PIL import Image


class TerrainGenerator:
    """
    Map a normalized greyscale heightmap to an RGB terrain map.
    """

    def __init__(self, regions=None):
        """
        regions: list of (min_elev, max_elev, (R,G,B)) tuples with elev in [0,1].
                 the default covers deep water → snow.
        """
        if regions is None:
            regions = [
                (0.00, 0.30, (  0,   0, 128)),  # deep water
                (0.30, 0.40, ( 64, 160, 224)),  # shallow water
                (0.40, 0.45, (238, 214, 175)),  # sand
                (0.45, 0.60, (120, 200,  80)),  # grassland
                (0.60, 0.75, ( 16, 128,  16)),  # forest
                (0.75, 0.90, (128, 128, 128)),  # mountain
                (0.90, 1.00, (255, 255, 255)),  # snow
            ]
        # Ensure sorted by min_elev
        self.regions = sorted(regions, key=lambda r: r[0])

    def apply(self, heightmap):
        """
        heightmap: PIL Image (mode 'L' or 'F') or 2D NumPy array of floats in [0,1].
        Returns a PIL.Image in mode 'RGB'.
        """
        # Load into normalized NumPy array
        if isinstance(heightmap, Image.Image):
            arr = np.asarray(heightmap.convert('F'), dtype=np.float32).copy()
            # assume input is [0,1] or [0,255]
            if arr.max() > 1.0:
                arr /= 255.0
        else:
            arr = np.array(heightmap, dtype=np.float32)
            arr = np.clip(arr, 0.0, 1.0)

        h, w = arr.shape
        rgb = np.zeros((h, w, 3), dtype=np.uint8)

        # Apply each region
        for min_e, max_e, color in self.regions:
            mask = (arr >= min_e) & (arr < max_e)
            rgb[mask] = color

        return Image.fromarray(rgb, mode='RGB')
