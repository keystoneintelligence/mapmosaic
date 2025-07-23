from enum import Enum
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QFrame, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from concurrent.futures import ThreadPoolExecutor
from images.processing import Corner
import os


class ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicked.emit()


class GridWidget(QWidget):
    """
    The third page of the workflow to display a grid of generated images,
    allow one to be selected, and expose the selected filepath and corner when continuing.
    """
    def __init__(self, output_fpath: str):
        super().__init__()
        main_layout = QVBoxLayout(self)

        # Source selector
        self.output_fpath = output_fpath
        self.source_combo = QComboBox()
        self.source_combo.addItems(["AI Generated", "Colorized"])
        self.source_combo.currentIndexChanged.connect(self.update_display)
        main_layout.addWidget(self.source_combo)

        instruction_label = QLabel("Select one image to seed the map")
        instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(instruction_label)

        # Grid of clickable labels
        self.grid_layout = QGridLayout()
        self.labels = []
        for pos in [(0,0), (0,1), (1,0), (1,1)]:
            lbl = ClickableLabel("…")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFrameShape(QFrame.Shape.Box)
            lbl.setMinimumSize(200, 200)
            lbl.index = len(self.labels)
            lbl.clicked.connect(lambda i=lbl.index: self.select_tile(i))
            self.labels.append(lbl)
            self.grid_layout.addWidget(lbl, *pos)

        main_layout.addLayout(self.grid_layout)

        # Continue button
        self.next_button = QPushButton("Continue to Confirmation")
        self.next_button.clicked.connect(self.on_next)
        main_layout.addWidget(self.next_button, alignment=Qt.AlignmentFlag.AlignRight)

        # Internal state
        self.image_generator = None
        self.generated_paths = [None] * 4
        self.colormap_pixmaps = [None] * 4
        self.colormap_paths = [None] * 4
        self.selected_index = None
        self.selected_path = None
        self.corner = None  # will hold selected Corner enum

    def set_grid_images(self, image_generator, colormap, description):
        """Generate AI tiles and colormap crops, then display them."""
        self.image_generator = image_generator
        crop_size = 64
        if colormap.isNull() or colormap.width() < crop_size or colormap.height() < crop_size:
            for lbl in self.labels:
                lbl.clear()
            return

        # Crop corners
        w, h = colormap.width(), colormap.height()
        coords = [
            (0, 0), (w - crop_size, 0),
            (0, h - crop_size), (w - crop_size, h - crop_size)
        ]
        temp_paths, pixmaps = [], []
        for i, (x, y) in enumerate(coords):
            crop = colormap.copy(x, y, crop_size, crop_size)
            path = os.path.join(self.output_fpath, f"crop_{i}.png")
            crop.save(path, "PNG")
            temp_paths.append(path)
            pixmaps.append(
                crop.scaled(200, 200,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.FastTransformation)
            )

        self.colormap_paths = temp_paths
        self.colormap_pixmaps = pixmaps

        # Generate AI images in parallel
        def _gen_corner(idx):
            try:
                return image_generator.generate_seed_image(
                    idx=idx,
                    working_dir=self.output_fpath,
                    reference_image=temp_paths[idx],
                    map_description=description
                )
            except Exception as e:
                print(f"[GridWidget] error gen tile {idx}: {e}")
                return None

        self.generated_paths = [None] * 4
        with ThreadPoolExecutor(max_workers=4) as exec:
            futures = {exec.submit(_gen_corner, i): i for i in range(4)}
            for fut, i in futures.items():
                try:
                    self.generated_paths[i] = fut.result(timeout=60)
                except Exception as e:
                    print(f"[GridWidget] tile {i} failed: {e}")

        self.update_display()

    def update_display(self):
        """Swap between AI images and colormap crops."""
        source = self.source_combo.currentText()
        items = (self.generated_paths if source == "AI Generated"
                 else self.colormap_pixmaps)
        for lbl, item in zip(self.labels, items):
            if isinstance(item, QPixmap):
                lbl.setPixmap(item)
            elif isinstance(item, str) and os.path.exists(item):
                pix = QPixmap(item).scaled(
                    200, 200,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                lbl.setPixmap(pix)
            else:
                lbl.setText("Failed")

        # Clear previous selection
        self.selected_index = None
        self.corner = None
        for lbl in self.labels:
            lbl.setStyleSheet("")

    def select_tile(self, idx: int):
        """Highlight the clicked tile and remember its index and corner."""
        self.selected_index = idx
        # Map index to Corner enum: 0->TOP_LEFT, 1->TOP_RIGHT, 2->BOTTOM_LEFT, 3->BOTTOM_RIGHT
        try:
            self.corner = Corner(idx + 1)
        except ValueError:
            self.corner = None

        for lbl in self.labels:
            lbl.setStyleSheet(
                "border: 3px solid yellow;" if lbl.index == idx else ""
            )

    def on_next(self):
        """When the continue button is pressed, stash the chosen filepath and corner."""
        if self.selected_index is None:
            print("No selection made!")
            return

        source = self.source_combo.currentText()
        if source == "AI Generated":
            self.selected_path = self.generated_paths[self.selected_index]
        else:
            self.selected_path = self.colormap_paths[self.selected_index]

        print(f"[GridWidget] selected file: {self.selected_path}")
        print(f"[GridWidget] selected corner: {self.corner}")
        # Now `self.selected_path` and `self.corner` are available for the next page to consume.
