import os
import numpy as np
from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSizePolicy, QSpinBox, QColorDialog, QApplication
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QPixmap, QColor, QMouseEvent, QImage, QFont, QPalette

from gui.paintable_label import PaintableLabel
from gui.multi_handle_slider import MultiHandleSlider


def pillow_to_pixmap(img: Image.Image) -> QPixmap:
    qimg = ImageQt(img.convert("RGBA"))
    return QPixmap.fromImage(qimg)


class FeatureMappingWidget(QWidget):
    def __init__(self):
        super().__init__()
        # === Force full white background ===
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("white"))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        self._press_pos = None
        self._dragging_btn = False

        self.heightmap: Image.Image | None = None
        self.colormap: Image.Image | None = None

        # Regions & default colors
        self.regions = [
            {"label": "Color 1", "color": QColor(0, 0, 128)},
            {"label": "Color 2", "color": QColor(64, 160, 224)},
            {"label": "Color 3", "color": QColor(238, 214, 175)},
            {"label": "Color 4", "color": QColor(120, 200, 80)},
            {"label": "Color 5", "color": QColor(16, 128, 16)},
            {"label": "Color 6", "color": QColor(128, 128, 128)},
        ]

        self.handle_buttons: list[QPushButton] = []
        layout = QVBoxLayout(self)

        # — Paintable preview —
        self.paintable_label = PaintableLabel()
        self.paintable_label.setAlignment(Qt.AlignCenter)
        self.paintable_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        layout.addWidget(self.paintable_label)
        layout.addStretch(1)

        # — Multi-handle slider —
        self.range_slider = MultiHandleSlider(Qt.Horizontal)
        self.range_slider.setRange(0, 100)
        self.range_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        n = len(self.regions)
        init = [int(90 * (i + 1) / n) for i in range(n)]
        self.range_slider.setValues(init)
        self.range_slider.valuesChanged.connect(self.update_colormap)
        layout.addWidget(self.range_slider)
        layout.addStretch(1)

        # Slider handle color buttons
        for idx, reg in enumerate(self.regions):
            btn = QPushButton("▼", self.range_slider)
            btn.setFixedSize(16, 16)
            # Transparent background, colored arrow
            btn.setStyleSheet(
                f"color: {reg['color'].name()};"
                "background-color: transparent;"
                "border: none;"
            )
            btn.setToolTip(reg["label"])
            btn.installEventFilter(self)
            self.range_slider.addHandleWidget(idx, btn)
            self.handle_buttons.append(btn)

        # — Controls —
        ctl = QHBoxLayout()
        ctl.setAlignment(Qt.AlignCenter)

        self.paint_toggle = QPushButton("Toggle Paint Mode")
        self.paint_toggle.setCheckable(True)
        self.paint_toggle.toggled.connect(self.paintable_label.set_painting_enabled)
        self.paint_toggle.toggled.connect(self._on_paint_toggled)
        ctl.addWidget(self.paint_toggle)

        self.brush_size = QSpinBox()
        self.brush_size.setRange(1, 100)
        self.brush_size.setValue(self.paintable_label.brush_size)
        self.brush_size.valueChanged.connect(self.paintable_label.set_brush_size)
        self.brush_size.setVisible(False)
        ctl.addWidget(self.brush_size)

        self.brush_color_btn = QPushButton()
        self.brush_color_btn.setFixedSize(24, 24)
        self.brush_color_btn.setStyleSheet(
            f"background-color: {self.paintable_label.brush_color.name()};"
        )
        self.brush_color_btn.clicked.connect(self._choose_brush_color)
        self.brush_color_btn.setVisible(False)
        ctl.addWidget(self.brush_color_btn)

        self.back_button = QPushButton("Back")
        self.cont_button = QPushButton("Continue")
        ctl.addWidget(self.back_button)
        ctl.addWidget(self.cont_button)

        layout.addLayout(ctl)

        # === Apply consistent styling to control buttons only ===
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        control_style = """
            QPushButton {
                background-color: #5c4d7d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #6e5a92;
            }
            QPushButton:pressed {
                background-color: #4d3c6a;
            }
        """
        for btn in (self.paint_toggle, self.back_button, self.cont_button):
            btn.setFont(font)
            btn.setFixedHeight(45)
            btn.setStyleSheet(control_style)

    def _on_paint_toggled(self, enabled: bool):
        """Show/hide brush size & color controls."""
        self.brush_size.setVisible(enabled)
        self.brush_color_btn.setVisible(enabled)

    def eventFilter(self, obj, event):
        if obj in self.handle_buttons:
            if event.type() == QEvent.MouseButtonPress:
                self._press_pos = event.pos()
                self._dragging_btn = False
                pos = obj.mapTo(self.range_slider, event.pos())
                mapped = QMouseEvent(
                    event.type(), pos,
                    event.button(), event.buttons(), event.modifiers()
                )
                self.range_slider.mousePressEvent(mapped)
                return True

            elif event.type() == QEvent.MouseMove:
                if (
                    self._press_pos
                    and (event.pos() - self._press_pos).manhattanLength()
                    > QApplication.startDragDistance()
                ):
                    self._dragging_btn = True
                if self._dragging_btn:
                    pos = obj.mapTo(self.range_slider, event.pos())
                    mapped = QMouseEvent(
                        event.type(), pos,
                        event.button(), event.buttons(), event.modifiers()
                    )
                    self.range_slider.mouseMoveEvent(mapped)
                return True

            elif event.type() == QEvent.MouseButtonRelease:
                pos = obj.mapTo(self.range_slider, event.pos())
                mapped = QMouseEvent(
                    event.type(), pos,
                    event.button(), event.buttons(), event.modifiers()
                )
                self.range_slider.mouseReleaseEvent(mapped)
                if not self._dragging_btn:
                    self.choose_color(self.handle_buttons.index(obj))
                self._press_pos = None
                self._dragging_btn = False
                return True

        return super().eventFilter(obj, event)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.paintable_label._refresh_scaled()
        self.range_slider._update_handle_widgets()

    def _choose_brush_color(self):
        col = QColorDialog.getColor(self.paintable_label.brush_color, self, "Select Brush Color")
        if col.isValid():
            self.paintable_label.set_brush_color(col)
            self.brush_color_btn.setStyleSheet(f"background-color: {col.name()};")

    def choose_color(self, idx: int):
        """Open color dialog for region idx, update button & recolor map."""
        region = self.regions[idx]
        current = region["color"]
        col = QColorDialog.getColor(current, self, f"Select color for {region['label']}")
        if col.isValid():
            region["color"] = col
            btn = self.handle_buttons[idx]
            btn.setStyleSheet(
                f"color: {col.name()}; background-color: transparent; border: none;"
            )
            self.update_colormap()

    def set_heightmap(self, img: Image.Image):
        self.heightmap = img.convert("L")
        self.update_colormap()

    def update_colormap(self, *_):
        if not self.heightmap:
            return

        arr = np.array(self.heightmap, dtype=np.float32) / 255.0
        h, w = arr.shape
        rgb = np.zeros((h, w, 3), dtype=np.uint8)

        vals = self.range_slider.values()
        bounds = [0.0] + [v / 100.0 for v in vals]
        for i, reg in enumerate(self.regions):
            lo, hi = bounds[i], bounds[i + 1]
            mask = (arr >= lo) & (arr < hi)
            c = reg["color"]
            rgb[mask] = [c.red(), c.green(), c.blue()]

        mask = arr >= bounds[-1]
        c = self.regions[-1]["color"]
        rgb[mask] = [c.red(), c.green(), c.blue()]

        self.colormap = Image.fromarray(rgb, "RGB")
        pix = pillow_to_pixmap(self.colormap)
        self.paintable_label.set_active_pixmap(pix)

    def get_colormap(self) -> Image.Image:
        pix = self.paintable_label.active_pixmap
        if pix:
            qimg = pix.toImage().convertToFormat(QImage.Format_RGBA8888)
            w, h = qimg.width(), qimg.height()
            mv = qimg.constBits()
            arr = np.frombuffer(mv, dtype=np.uint8).reshape(h, w, 4)
            rgb = arr[..., :3]
            return Image.fromarray(rgb, "RGB")
        return self.colormap

    def save_colormap(self, folder: str):
        img = self.get_colormap()
        if img:
            path = os.path.join(folder, "featuremap.png")
            img.save(path)
