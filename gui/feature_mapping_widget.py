import os
import numpy as np
from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSizePolicy, QSpinBox, QColorDialog, QApplication
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QPixmap, QColor, QMouseEvent

from gui.paintable_label import PaintableLabel
from gui.multi_handle_slider import MultiHandleSlider


def pillow_to_pixmap(img: Image.Image) -> QPixmap:
    qimage = ImageQt(img.convert("RGBA"))
    return QPixmap.fromImage(qimage)


class FeatureMappingWidget(QWidget):
    """
    Widget for colorizing a heightmap based on elevation regions and
    hand-painting features, using a single multi-handle slider.
    """
    def __init__(self):
        super().__init__()
        self._press_pos = None
        self._dragging_btn = False

        self.heightmap: Image.Image | None = None
        self.colormap: Image.Image | None = None
        self.preview_pixmap: QPixmap | None = None

        # Define regions with default colors
        self.regions = [
            {"label": "Color 1",    "color": QColor(0,   0,   128)},
            {"label": "Color 2",    "color": QColor(64,  160, 224)},
            {"label": "Color 3",    "color": QColor(238, 214, 175)},
            {"label": "Color 4",    "color": QColor(120, 200,  80)},
            {"label": "Color 5",    "color": QColor(16,  128,  16)},
            {"label": "Color 6",    "color": QColor(128, 128, 128)},
        ]

        self.handle_buttons: list[QPushButton] = []

        main_layout = QVBoxLayout(self)

        # Preview area
        self.paintable_label = PaintableLabel()
        self.paintable_label.setAlignment(Qt.AlignCenter)
        self.paintable_label.setScaledContents(False)
        self.paintable_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        main_layout.addWidget(self.paintable_label)

        # Stretch to push slider towards vertical center
        main_layout.addStretch(1)

        # --- Slider setup ---
        self.range_slider = MultiHandleSlider(Qt.Horizontal)
        self.range_slider.setRange(0, 100)
        self.range_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        count = len(self.regions)
        init_vals = [int(90 * (i + 1) / count) for i in range(count)]
        self.range_slider.setValues(init_vals)
        self.range_slider.valuesChanged.connect(self.update_from_slider)
        main_layout.addWidget(self.range_slider)

        # Stretch below slider
        main_layout.addStretch(1)
        # ----------------------------------------------------

        # Create a handle button for each region
        for idx, region in enumerate(self.regions):
            btn = QPushButton('▼', self.range_slider)
            btn.setFixedSize(16, 16)
            btn.setStyleSheet(
                f"color: {region['color'].name()}; background: transparent; border: none;"
            )
            btn.setToolTip(region['label'])
            btn.installEventFilter(self)
            self.range_slider.addHandleWidget(idx, btn)
            self.handle_buttons.append(btn)

        # Controls: paint toggle, brush size/color, navigation
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)

        self.paint_toggle = QPushButton("Toggle Paint Mode")
        self.paint_toggle.setCheckable(True)
        self.paint_toggle.toggled.connect(self.paintable_label.set_painting_enabled)
        self.paint_toggle.toggled.connect(self._on_paint_toggled)
        btn_layout.addWidget(self.paint_toggle)

        self.brush_size_spin = QSpinBox()
        self.brush_size_spin.setRange(1, 100)
        self.brush_size_spin.setValue(self.paintable_label.brush_size)
        self.brush_size_spin.valueChanged.connect(self.paintable_label.set_brush_size)
        self.brush_size_spin.setVisible(False)
        btn_layout.addWidget(self.brush_size_spin)

        self.brush_color_btn = QPushButton()
        self.brush_color_btn.setFixedSize(24, 24)
        init_col = QColor(self.paintable_label.brush_color)
        self.brush_color_btn.setStyleSheet(f"background-color: {init_col.name()};")
        self.brush_color_btn.clicked.connect(self._choose_brush_color)
        self.brush_color_btn.setVisible(False)
        btn_layout.addWidget(self.brush_color_btn)

        self.back_button = QPushButton("Back")
        self.next_button = QPushButton("Continue")
        btn_layout.addWidget(self.back_button)
        btn_layout.addWidget(self.next_button)

        main_layout.addLayout(btn_layout)

    def eventFilter(self, obj, event):
        # Handle press/move/release on handle buttons to support drag + click
        if obj in self.handle_buttons:
            if event.type() == QEvent.MouseButtonPress:
                self._press_pos = event.pos()
                self._dragging_btn = False
                pos = obj.mapTo(self.range_slider, event.pos())
                mapped = QMouseEvent(event.type(), pos,
                                     event.button(), event.buttons(), event.modifiers())
                self.range_slider.mousePressEvent(mapped)
                return True
            elif event.type() == QEvent.MouseMove:
                if self._press_pos and (event.pos() - self._press_pos).manhattanLength() > QApplication.startDragDistance():
                    self._dragging_btn = True
                if self._dragging_btn:
                    pos = obj.mapTo(self.range_slider, event.pos())
                    mapped = QMouseEvent(event.type(), pos,
                                         event.button(), event.buttons(), event.modifiers())
                    self.range_slider.mouseMoveEvent(mapped)
                return True
            elif event.type() == QEvent.MouseButtonRelease:
                pos = obj.mapTo(self.range_slider, event.pos())
                mapped = QMouseEvent(event.type(), pos,
                                     event.button(), event.buttons(), event.modifiers())
                self.range_slider.mouseReleaseEvent(mapped)
                if not self._dragging_btn:
                    idx = self.handle_buttons.index(obj)
                    self.choose_color(idx)
                self._press_pos = None
                self._dragging_btn = False
                return True
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._scale_preview()
        self.range_slider._update_handle_widgets()

    def _scale_preview(self):
        if not self.preview_pixmap:
            return
        scaled = self.preview_pixmap.scaled(
            self.paintable_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.paintable_label.setPixmap(scaled)

    def _on_paint_toggled(self, enabled: bool):
        self.brush_size_spin.setVisible(enabled)
        self.brush_color_btn.setVisible(enabled)

    def _choose_brush_color(self):
        current = QColor(self.paintable_label.brush_color)
        col = QColorDialog.getColor(current, self, "Select Brush Color")
        if col.isValid():
            self.paintable_label.set_brush_color(col)
            self.brush_color_btn.setStyleSheet(f"background-color: {col.name()};")

    def choose_color(self, idx: int):
        region = self.regions[idx]
        current = region['color']
        col = QColorDialog.getColor(current, self, f"Select color for {region['label']}")
        if col.isValid():
            region['color'] = col
            btn = self.handle_buttons[idx]
            btn.setStyleSheet(f"color: {col.name()}; background: transparent; border: none;")
            self.update_colormap()

    def set_heightmap(self, heightmap: Image.Image):
        self.heightmap = heightmap.convert('L')
        self.update_colormap()

    def update_from_slider(self, values: list[int]):
        self.update_colormap()

    def update_colormap(self):
        if not self.heightmap:
            return
        arr = np.array(self.heightmap, dtype=np.float32) / 255.0
        h, w = arr.shape
        rgb = np.zeros((h, w, 3), dtype=np.uint8)

        vals = self.range_slider.values()
        bounds = [0.0] + [v / 100.0 for v in vals]

        for idx, region in enumerate(self.regions):
            lo, hi = bounds[idx], bounds[idx + 1]
            mask = (arr >= lo) & (arr < hi)
            c = region['color']
            rgb[mask] = [c.red(), c.green(), c.blue()]

        last_bound = bounds[-1]
        mask = arr >= last_bound
        c = self.regions[-1]['color']
        rgb[mask] = [c.red(), c.green(), c.blue()]

        self.colormap = Image.fromarray(rgb, mode='RGB')
        self.preview_pixmap = pillow_to_pixmap(self.colormap)
        self._scale_preview()

    def get_colormap(self) -> Image.Image:
        return self.colormap

    def save_colormap(self, folder: str):
        if not self.colormap:
            return
        path = os.path.join(folder, 'featuremap.png')
        self.colormap.save(path)
