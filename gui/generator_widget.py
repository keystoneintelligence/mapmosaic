import os
from typing import Tuple
from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QComboBox, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage

from inference.openai import OpenAIImageGenerator

from images.processing import (
    place_image_at,
    get_image_at,
    place_image_in_corner,
    get_overlay_positions,
    Corner,
)


class GeneratorWidget(QWidget):
    """
    A widget that generates a tiled image by repeatedly placing a seed overlay,
    with optional colormap-backed view.
    """
    def __init__(self, output_fpath: str, parent=None):
        super().__init__(parent)
        # — State —
        self.output_fpath = output_fpath
        self.seed: Image.Image | None = None
        self.size = 0
        self.corner: Corner | None = None

        self.current_nomap: Image.Image | None = None
        self.current_withmap: Image.Image | None = None
        self._colormap_bg: Image.Image | None = None

        self.positions: list[Tuple[int,int]] = []
        self._index = 0
        self._cancelled = False

        # — UI —
        self.view_combo = QComboBox()
        self.view_combo.addItems(["With colormap", "Without colormap"])
        self.view_combo.currentIndexChanged.connect(self._update_display)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(True)

        self.next_button = QPushButton("Continue")
        # you could hook up manual stepping:
        # self.next_button.clicked.connect(self._process_next)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_generation)

        layout = QVBoxLayout(self)
        layout.addWidget(self.view_combo)
        layout.addWidget(self.image_label, stretch=1)
        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(self.cancel_button)
        btns.addWidget(self.next_button)
        layout.addLayout(btns)

    def generate(
        self,
        seed_fpath: str,
        size: int,
        corner: Corner,
        colormap_pixmap: QPixmap,
        image_generator: OpenAIImageGenerator,
        map_description: str,
    ):
        """
        Args:
          seed_fpath:      path to your seed image
          size:            output dimensions (square)
          corner:          which corner to start tiling from
          colormap_pixmap:    a QPixmap to use as the background colormap
        """
        self.image_generator = image_generator
        self.map_description = map_description
        self._cancelled = False
        self.size = size
        self.corner = corner

        # load seed
        self.seed = Image.open(seed_fpath).convert("RGBA")

        # scale the incoming QPixmap to our target size, then convert to PIL
        scaled = colormap_pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        qimg: QImage = scaled.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        w, h = qimg.width(), qimg.height()
        # bits() returns a memoryview; just turn it into bytes
        buf = qimg.bits().tobytes()
        # now create a PIL image from the raw RGBA data
        self._colormap_bg = Image.frombytes("RGBA", (w, h), buf)

        # build initial frames
        self.current_nomap = place_image_in_corner(size, self.seed, corner)
        self.current_withmap = Image.alpha_composite(
            self._colormap_bg, self.current_nomap
        )

        # precompute overlay positions
        self.positions = get_overlay_positions(size, self.seed, corner)
        self._index = 0

        # default view and display
        self.view_combo.setCurrentIndex(0)  # “With colormap”
        self._update_display()

        # kick off the loop
        QTimer.singleShot(0, self._process_next)

    def cancel_generation(self):
        self._cancelled = True
        self.cancel_button.setEnabled(False)
        self.next_button.setEnabled(False)

    def _update_display(self):
        # pick which variant to show
        img = (
            self.current_withmap
            if self.view_combo.currentIndex() == 0
            else self.current_nomap
        )
        if img is None:
            return

        qtimg = ImageQt(img)
        pix = QPixmap.fromImage(qtimg)
        sz = self.image_label.size()
        if not sz.isEmpty():
            pix = pix.scaled(
                sz,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        self.image_label.setPixmap(pix)

    def _generate_next_frame(self, idx: int, pos: Tuple[int, int]) -> Image.Image:
        """
        Grab the region “beneath” where the seed would go and
        detect any fully transparent pixels.

        Returns the patch to overlay for this step.
        """
        mask = get_image_at(self.current_nomap, self.seed.size, pos)
        colormap = get_image_at(self.current_withmap, self.seed.size, pos)
        alpha = mask.split()[-1]
        min_a, _ = alpha.getextrema()
        if min_a == 0:
            # TODO: need to clean up the types of objects I am passing around
            # in terms of images vs paths
            reference_path = os.path.join(self.output_fpath, f"ref_{idx}_tmp.png")
            mask_path = os.path.join(self.output_fpath, f"mask_{idx}_tmp.png")
            colormap.save(reference_path)
            mask.save(mask_path)
            patch_str = self.image_generator.generate_mosaic_image(
                idx=idx,
                working_dir=self.output_fpath,
                reference_image=reference_path,
                mask_path=mask_path,
                map_description=self.map_description,
            )
            return Image.open(patch_str)
        return colormap

    def _process_next(self):
        if self._cancelled:
            return

        if self._index < len(self.positions):
            pos = self.positions[self._index]

            before_path = os.path.join(self.output_fpath, f"before_{self._index}.png")
            self.current_nomap.save(before_path)

            print(f"[DEBUG] placing tile #{self._index} at {pos}")

            # use your custom frame logic
            patch = self._generate_next_frame(self._index, pos)

            # update the no-map mosaic
            self.current_nomap = place_image_at(
                self.current_nomap, patch, pos
            )

            # re-composite the colormap-backed variant
            self.current_withmap = Image.alpha_composite(
                self._colormap_bg, self.current_nomap
            )

            after_path = os.path.join(self.output_fpath, f"after_{self._index}.png")
            self.current_nomap.save(after_path)

            self._index += 1
            QApplication.processEvents()
            self._update_display()
            QTimer.singleShot(0, self._process_next)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_display()
