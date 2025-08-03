from enum import Enum
from PIL import Image
from typing import List, Tuple
from PySide6.QtGui import QPixmap
from PIL.ImageQt import ImageQt


class Corner(Enum):
    TOP_LEFT = 1
    TOP_RIGHT = 2
    BOTTOM_LEFT = 3
    BOTTOM_RIGHT = 4


def place_image_in_corner(n: int, overlay: Image.Image, corner: Corner) -> Image.Image:
    """
    Create an n×n transparent canvas and paste the overlay (m×m or smaller)
    into the specified corner, delegating the actual paste to place_image_at().

    Args:
        n: Size (width and height) of the square transparent canvas.
        overlay: A PIL Image (must be ≤ n×n).
        corner: One of Corner.TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT.

    Returns:
        A new PIL Image (mode 'RGBA') with the overlay pasted.
    """
    # Prepare images
    overlay_rgba = overlay.convert("RGBA")
    base = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    m_w, m_h = overlay_rgba.size
    if m_w > n or m_h > n:
        raise ValueError(f"Overlay ({m_w}×{m_h}) is larger than base ({n}×{n}).")

    # Compute corner positions
    positions: dict[Corner, Tuple[int, int]] = {
        Corner.TOP_LEFT:     (0,       0),
        Corner.TOP_RIGHT:    (n - m_w, 0),
        Corner.BOTTOM_LEFT:  (0,       n - m_h),
        Corner.BOTTOM_RIGHT: (n - m_w, n - m_h),
    }
    try:
        pos = positions[corner]
    except KeyError:
        raise ValueError(f"Unknown corner: {corner!r}")

    # Delegate to the generic placer
    return place_image_at(base, overlay_rgba, pos)


def place_image_at(
    base: Image.Image,
    overlay: Image.Image,
    position: Tuple[int, int]
) -> Image.Image:
    """
    Paste the overlay image onto the base image at the given (x, y) position.

    Args:
        base:     A PIL Image (usually the larger “current” image).
        overlay:  A PIL Image to paste (the smaller “to_add” image).
        position: Tuple (x, y) where the top-left of `overlay` will go on `base`.

    Returns:
        A new PIL Image (mode 'RGBA') with the overlay pasted at `position`.
    """
    # Ensure both images have an alpha channel
    base_rgba = base.convert("RGBA")
    overlay_rgba = overlay.convert("RGBA")

    # Work on a copy so we don’t mutate the original
    result = base_rgba.copy()

    # Paste overlay using its alpha channel as mask
    result.paste(overlay_rgba, position, overlay_rgba)
    return result


def get_image_at(
    base: Image.Image,
    size: Tuple[int, int],
    position: Tuple[int, int]
) -> Image.Image:
    """
    Extract a sub-image of given size from `base` at the given (x, y) position.

    Args:
        base:     A PIL Image (usually the larger “current” image).
        size:     Tuple (width, height) of the region to extract.
        position: Tuple (x, y) where the top-left of the region starts.

    Returns:
        A new PIL Image (mode 'RGBA') of dimensions `size` cropped from `base`.

    Raises:
        ValueError: if the requested region lies partially or wholly outside `base`.
    """
    # Ensure RGBA and work on a copy
    base_rgba = base.convert("RGBA")
    x, y = position
    w, h = size
    bw, bh = base_rgba.size

    # Bounds check
    if x < 0 or y < 0 or x + w > bw or y + h > bh:
        raise ValueError(
            f"Requested region {size} at {position} "
            f"is out of base image bounds {base_rgba.size}."
        )

    # Crop and return
    region = base_rgba.crop((x, y, x + w, y + h))
    return region


def get_overlay_positions(
    base_size: int,
    overlay: Image.Image,
    corner: Corner
) -> List[Tuple[int, int]]:
    """
    Generate a list of (x, y) positions to tile a square overlay across an
    n×n base image, stepping by half the overlay size in both directions.

    Args:
        base_size: Width and height (n) of the square base image.
        overlay:    PIL Image to tile (m×m or smaller).
        corner:     Which corner to start from.

    Returns:
        List of (x, y) coordinates in the order they should be visited.
    """
    m_w, m_h = overlay.size
    if m_w > base_size or m_h > base_size:
        raise ValueError("Overlay is larger than the base image.")

    # stride is half the overlay dimension
    stride_x = m_w // 2
    stride_y = m_h // 2
    if stride_x == 0 or stride_y == 0:
        raise ValueError("Overlay too small to compute a half-step stride.")

    # Determine start, end, and step for x and y based on corner
    if corner == Corner.TOP_LEFT:
        start_x, end_x, step_x = 0, base_size - m_w,  stride_x
        start_y, end_y, step_y = 0, base_size - m_h,  stride_y
    elif corner == Corner.TOP_RIGHT:
        start_x, end_x, step_x = base_size - m_w, 0, -stride_x
        start_y, end_y, step_y = 0, base_size - m_h,  stride_y
    elif corner == Corner.BOTTOM_LEFT:
        start_x, end_x, step_x = 0, base_size - m_w,  stride_x
        start_y, end_y, step_y = base_size - m_h, 0, -stride_y
    elif corner == Corner.BOTTOM_RIGHT:
        start_x, end_x, step_x = base_size - m_w, 0, -stride_x
        start_y, end_y, step_y = base_size - m_h, 0, -stride_y
    else:
        raise ValueError(f"Unsupported corner: {corner!r}")

    # Build the list of x positions
    xs: List[int] = []
    x = start_x
    if step_x > 0:
        while x <= end_x:
            xs.append(x)
            x += step_x
    else:
        while x >= end_x:
            xs.append(x)
            x += step_x

    # Build the list of y positions
    ys: List[int] = []
    y = start_y
    if step_y > 0:
        while y <= end_y:
            ys.append(y)
            y += step_y
    else:
        while y >= end_y:
            ys.append(y)
            y += step_y

    # Combine into (x, y) pairs for each row, in the same x-direction each time
    coords: List[Tuple[int, int]] = []
    for y in ys:
        for x in xs:
            coords.append((x, y))

    return coords


def pillow_to_pixmap(img: Image.Image) -> QPixmap:
    qimg = ImageQt(img.convert("RGBA"))
    return QPixmap.fromImage(qimg)
