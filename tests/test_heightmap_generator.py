import numpy as np
import pytest
from PIL import Image
from noise.heightmap_generator import HeightmapGenerator  # ← adjust this import

def test_generate_small_reproducible_and_in_bounds():
    # arrange
    width, height = 3, 3
    seed = 42

    # act
    gen1 = HeightmapGenerator(seed=seed, octaves=1)
    img1 = gen1.generate(width, height)

    gen2 = HeightmapGenerator(seed=seed, octaves=1)
    img2 = gen2.generate(width, height)

    # assert
    # 1) correct type, mode and size
    assert isinstance(img1, Image.Image)
    assert img1.mode == "L"
    assert img1.size == (width, height)

    # 2) reproducibility
    arr1 = np.array(img1)
    arr2 = np.array(img2)
    assert np.array_equal(arr1, arr2)

    # 3) pixel values stay in 0–255
    assert arr1.min() >= 0
    assert arr1.max() <= 255
