# feature_mapping_widget.py
import os
import numpy as np
from PIL import Image
from PIL.ImageQt import fromqimage
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QDoubleSpinBox, QSpinBox, QColorDialog, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor, QPainter

from gui.paintable_label import PaintableLabel


def pillow_to_pixmap(img: Image.Image) -> QPixmap:
    from PIL.ImageQt import ImageQt
    qimage = ImageQt(img.convert("RGBA"))
    return QPixmap.fromImage(qimage)


class FeatureMappingWidget(QWidget):
    """
    Widget for colorizing a heightmap based on elevation regions and
    optionally hand-painting features.
    """
    def __init__(self):
        super().__init__()
        self.heightmap: Image.Image | None = None
        self.colormap: Image.Image | None = None
        self.preview_pixmap: QPixmap | None = None

        self.regions = [
            {"label": "Deep Water",    "min": 0.00, "max": 0.30, "color": QColor(0, 0, 128)},
            {"label": "Shallow Water", "min": 0.30, "max": 0.40, "color": QColor(64, 160, 224)},
            {"label": "Sand",          "min": 0.40, "max": 0.45, "color": QColor(238, 214, 175)},
            {"label": "Grassland",     "min": 0.45, "max": 0.60, "color": QColor(120, 200, 80)},
            {"label": "Forest",        "min": 0.60, "max": 0.75, "color": QColor(16, 128, 16)},
            {"label": "Mountain",      "min": 0.75, "max": 1.00, "color": QColor(128, 128, 128)},
        ]

        main_layout = QVBoxLayout(self)

        # Preview area (paintable) — scaled to fit, no scrollbars
        self.paintable_label = PaintableLabel()
        self.paintable_label.setAlignment(Qt.AlignCenter)
        self.paintable_label.setScaledContents(True)
        self.paintable_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        main_layout.addWidget(self.paintable_label, stretch=1)

        # Region controls grid
        grid = QGridLayout()
        grid.addWidget(QLabel("Region"), 0, 0)
        grid.addWidget(QLabel("Min"), 0, 1)
        grid.addWidget(QLabel("Max"), 0, 2)
        grid.addWidget(QLabel("Color"), 0, 3)
        for i, region in enumerate(self.regions, start=1):
            grid.addWidget(QLabel(region["label"]), i, 0)
            min_spin = QDoubleSpinBox()
            min_spin.setRange(0.0, 1.0)
            min_spin.setSingleStep(0.01)
            min_spin.setValue(region["min"])
            min_spin.valueChanged.connect(self.update_colormap)
            grid.addWidget(min_spin, i, 1)
            region["min_spin"] = min_spin

            max_spin = QDoubleSpinBox()
            max_spin.setRange(0.0, 1.0)
            max_spin.setSingleStep(0.01)
            max_spin.setValue(region["max"])
            max_spin.valueChanged.connect(self.update_colormap)
            grid.addWidget(max_spin, i, 2)
            region["max_spin"] = max_spin

            color_btn = QPushButton()
            color_btn.setFixedSize(24, 24)
            color_btn.setStyleSheet(f"background-color: {region['color'].name()};")
            color_btn.clicked.connect(lambda _, r=region: self.choose_color(r))
            grid.addWidget(color_btn, i, 3)
            region["color_btn"] = color_btn

        main_layout.addLayout(grid)

        # Controls: paint toggle, brush settings, navigation
        btn_layout = QHBoxLayout()
        # Paint mode toggle
        self.paint_toggle = QPushButton("Toggle Paint Mode")
        self.paint_toggle.setCheckable(True)
        self.paint_toggle.toggled.connect(self.paintable_label.set_painting_enabled)
        self.paint_toggle.toggled.connect(self._on_paint_toggled)
        btn_layout.addWidget(self.paint_toggle)

        # Brush Size
        self.brush_size_label = QLabel("Brush Size:")
        self.brush_size_label.setVisible(False)
        btn_layout.addWidget(self.brush_size_label)
        self.brush_size_spin = QSpinBox()
        self.brush_size_spin.setRange(1, 100)
        self.brush_size_spin.setValue(self.paintable_label.brush_size)
        self.brush_size_spin.valueChanged.connect(self.paintable_label.set_brush_size)
        self.brush_size_spin.setVisible(False)
        btn_layout.addWidget(self.brush_size_spin)

        # Brush Color
        self.brush_color_label = QLabel("Brush Color:")
        self.brush_color_label.setVisible(False)
        btn_layout.addWidget(self.brush_color_label)
        self.brush_color_btn = QPushButton()
        self.brush_color_btn.setFixedSize(24, 24)
        init_col = QColor(self.paintable_label.brush_color)
        self.brush_color_btn.setStyleSheet(f"background-color: {init_col.name()};")
        self.brush_color_btn.clicked.connect(self._choose_brush_color)
        self.brush_color_btn.setVisible(False)
        btn_layout.addWidget(self.brush_color_btn)

        btn_layout.addStretch(1)
        self.back_button = QPushButton("Back")
        self.next_button = QPushButton("Continue")
        btn_layout.addWidget(self.back_button)
        btn_layout.addWidget(self.next_button)
        main_layout.addLayout(btn_layout)

    def _on_paint_toggled(self, enabled: bool):
        # Show or hide brush settings based on paint mode
        self.brush_size_label.setVisible(enabled)
        self.brush_size_spin.setVisible(enabled)
        self.brush_color_label.setVisible(enabled)
        self.brush_color_btn.setVisible(enabled)

    def _choose_brush_color(self):
        init_col = QColor(self.paintable_label.brush_color)
        col = QColorDialog.getColor(init_col, self, "Select Brush Color")
        if col.isValid():
            self.paintable_label.set_brush_color(col)
            self.brush_color_btn.setStyleSheet(f"background-color: {col.name()};")

    def choose_color(self, region: dict):
        col = QColorDialog.getColor(region["color"], self, f"Select color for {region['label']}")
        if col.isValid():
            region["color"] = col
            region["color_btn"].setStyleSheet(f"background-color: {col.name()};")
            self.update_colormap()

    def set_heightmap(self, heightmap: Image.Image):
        self.heightmap = heightmap.convert("L")
        self.update_colormap()

    def update_colormap(self):
        if not self.heightmap:
            return
        arr = np.array(self.heightmap, dtype=np.float32) / 255.0
        h, w = arr.shape
        rgb = np.zeros((h, w, 3), dtype=np.uint8)
        for region in self.regions:
            lo = region["min_spin"].value()
            hi = region["max_spin"].value()
            mask = (arr >= lo) & (arr < hi)
            col = region["color"]
            rgb[mask] = [col.red(), col.green(), col.blue()]
        self.colormap = Image.fromarray(rgb, mode="RGB")
        pix = pillow_to_pixmap(self.colormap)
        self.preview_pixmap = pix
        self.paintable_label.set_active_pixmap(pix)

    def get_colormap(self) -> "PIL.Image.Image":
        # Return the full-res pixmap (with any paint) as a PIL image
        return fromqimage(self.paintable_label.active_pixmap.toImage())

    def save_colormap(self, folder: str):
        if not self.colormap:
            return
        final = self.get_colormap()
        path = os.path.join(folder, "featuremap.png")
        final.save(path)
