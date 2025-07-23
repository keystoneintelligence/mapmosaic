import os
import pytest
from PIL import Image
from images.processing import get_image_at, place_image_at, place_image_in_corner, get_overlay_positions, Corner

# Directory where test outputs will be written
TEST_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

@pytest.fixture(scope="session", autouse=True)
def make_output_dir():
    """Ensure the output directory exists before any tests run."""
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)

@pytest.mark.parametrize("corner", [
    Corner.TOP_LEFT,
    Corner.TOP_RIGHT,
    Corner.BOTTOM_LEFT,
    Corner.BOTTOM_RIGHT,
])
def test_place_image_in_corner(corner):
    n = 20  # size of the transparent base
    m = 5   # size of the overlay
    overlay_color = (123, 222,  56, 255)
    # create a solid‐color m×m overlay
    overlay = Image.new("RGBA", (m, m), overlay_color)

    # run the function under test
    result = place_image_in_corner(n, overlay, corner)

    # save the output for manual inspection if needed
    out_path = os.path.join(TEST_OUTPUT_DIR, f"{corner.name}.png")
    result.save(out_path)

    # map each corner to its expected top‐left coordinate
    positions = {
        Corner.TOP_LEFT:     (0,     0),
        Corner.TOP_RIGHT:    (n - m, 0),
        Corner.BOTTOM_LEFT:  (0,     n - m),
        Corner.BOTTOM_RIGHT: (n - m, n - m),
    }
    exp_x, exp_y = positions[corner]

    # check a pixel well inside the overlay region
    cx = exp_x + m // 2
    cy = exp_y + m // 2
    assert result.getpixel((cx, cy)) == overlay_color

    # check a pixel in the opposite corner is still transparent
    opp_x = 0 if exp_x > 0 else n - 1
    opp_y = 0 if exp_y > 0 else n - 1
    assert result.getpixel((opp_x, opp_y))[3] == 0  # alpha == 0


@pytest.mark.parametrize("position", [
    (0, 0),      # top-left
    (6, 0),      # top-right-ish
    (0, 6),      # bottom-left-ish
    (6, 6),      # bottom-right
])
def test_place_image_at(position):
    base_size = 10
    overlay_size = 4
    overlay_color = (200, 100, 50, 128)  # semi-opaque

    # create base & overlay
    base = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
    overlay = Image.new("RGBA", (overlay_size, overlay_size), overlay_color)

    result = place_image_at(base, overlay, position)
    x0, y0 = position

    # a pixel well inside the overlay region
    inside_x = x0 + overlay_size // 2
    inside_y = y0 + overlay_size // 2

    # compute expected blend:  result = overlay * (α/255) + base * (1 – α/255)
    α = overlay_color[3]
    mask = α / 255
    expected = (
        round(overlay_color[0] * mask),
        round(overlay_color[1] * mask),
        round(overlay_color[2] * mask),
        round(α * mask),
    )

    assert result.getpixel((inside_x, inside_y)) == expected

    # and just outside the overlay should remain fully transparent
    outside_x = x0 - 1 if x0 > 0 else x0 + overlay_size
    outside_y = y0 - 1 if y0 > 0 else y0 + overlay_size
    assert 0 <= outside_x < base_size and 0 <= outside_y < base_size
    assert result.getpixel((outside_x, outside_y))[3] == 0  # still α=0


@pytest.mark.parametrize("corner", [
    Corner.TOP_LEFT,
    Corner.TOP_RIGHT,
    Corner.BOTTOM_LEFT,
    Corner.BOTTOM_RIGHT,
])
def test_full_coverage(corner):
    base_size = 10
    overlay_size = 4
    # a dummy overlay—only its size() is used
    overlay = Image.new("RGBA", (overlay_size, overlay_size), (0, 0, 0, 0))

    # get all top-left positions for this corner
    positions = get_overlay_positions(base_size, overlay, corner)

    # build a coverage grid
    covered = [[False] * base_size for _ in range(base_size)]
    for x, y in positions:
        for dx in range(overlay_size):
            for dy in range(overlay_size):
                px = x + dx
                py = y + dy
                if 0 <= px < base_size and 0 <= py < base_size:
                    covered[py][px] = True

    # assert every pixel is covered by at least one overlay
    for row in range(base_size):
        for col in range(base_size):
            assert covered[row][col], f"Pixel ({col},{row}) not covered when starting at {corner}"

def test_get_image_at_valid_and_invalid():
    base_size = 8
    base = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
    # fill base with unique pixels
    for x in range(base_size):
        for y in range(base_size):
            base.putpixel((x, y), (x, y, (x + y) % 256, 255))

    # valid extraction
    w, h = 4, 3
    x0, y0 = 2, 1
    region = get_image_at(base, size=(w, h), position=(x0, y0))
    assert region.size == (w, h)
    # verify top-left and bottom-right of region match source
    assert region.getpixel((0, 0)) == base.getpixel((x0, y0))
    assert region.getpixel((w - 1, h - 1)) == base.getpixel((x0 + w - 1, y0 + h - 1))

    # out-of-bounds should raise
    with pytest.raises(ValueError):
        get_image_at(base, size=(5, 5), position=(5, 5))
