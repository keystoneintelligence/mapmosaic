# tests/test_terrain_generator.py

import numpy as np
import pytest
from PIL import Image
from noise.terrain_generator import TerrainGenerator  # adjust import to where you defined it

def test_terrain_generator_apply_correct_mapping_and_output():
    # 1×7 heightmap with one sample in each default region
    height_values = [0.15, 0.35, 0.425, 0.525, 0.675, 0.825, 0.95]
    heightmap = np.array([height_values], dtype=np.float32)  # shape = (1, 7)

    tg = TerrainGenerator()
    result = tg.apply(heightmap)

    # -- Type, mode and size
    assert isinstance(result, Image.Image)
    assert result.mode == "RGB"
    # width should be 7, height 1
    assert result.size == (7, 1)

    # -- Check that each pixel matches the region color
    expected_colors = [
        (  0,   0, 128),  # deep water
        ( 64, 160, 224),  # shallow water
        (238, 214, 175),  # sand
        (120, 200,  80),  # grassland
        ( 16, 128,  16),  # forest
        (128, 128, 128),  # mountain
        (255, 255, 255),  # snow
    ]

    px = result.load()
    for x, exp in enumerate(expected_colors):
        assert px[x, 0] == exp, f"Pixel at x={x} was {px[x,0]}, expected {exp}"
