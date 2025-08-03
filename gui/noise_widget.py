from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QDoubleSpinBox, QSpinBox, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor, QFont

from noise.heightmap_generator import HeightmapGenerator
from images.processing import pillow_to_pixmap


class NoiseWidget(QWidget):
    """
    Styled widget for tuning noise parameters and previewing the generated heightmap.
    """
    def __init__(self):
        super().__init__()
        self.config = None
        self.generator = None
        self.preview_size = (512, 512)

        # === White background ===
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("white"))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        # === Main vertical layout ===
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(25)

        # === Centered, flexible preview label ===
        self.preview_label = QLabel(alignment=Qt.AlignCenter)
        # allow it to shrink/expand instead of fixed-sizing
        self.preview_label.setMinimumSize(*self.preview_size)
        self.preview_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        self.preview_label.setStyleSheet("border: 1px solid #ddd;")
        preview_container = QHBoxLayout()
        preview_container.addStretch(1)
        preview_container.addWidget(self.preview_label)
        preview_container.addStretch(1)
        main_layout.addLayout(preview_container)

        # push controls down when there’s extra space
        main_layout.addStretch(1)

        # === Noise parameter controls ===
        control_layout = QGridLayout()
        control_layout.setHorizontalSpacing(12)
        control_layout.setVerticalSpacing(10)

        def add_control(label, widget, row):
            control_layout.addWidget(QLabel(label), row, 0)
            control_layout.addWidget(widget, row, 1)

        # initialize spinboxes
        self.base_freq_spin = QDoubleSpinBox()
        self.base_freq_spin.setDecimals(3)
        self.base_freq_spin.setRange(0.0001, 0.1)
        self.base_freq_spin.setSingleStep(0.0001)
        self.base_freq_spin.setValue(0.005)

        self.octaves_spin = QSpinBox()
        self.octaves_spin.setRange(1, 10)
        self.octaves_spin.setValue(6)

        self.lacunarity_spin = QDoubleSpinBox()
        self.lacunarity_spin.setDecimals(3)
        self.lacunarity_spin.setRange(1.0, 4.0)
        self.lacunarity_spin.setSingleStep(0.1)
        self.lacunarity_spin.setValue(2.2)

        self.gain_spin = QDoubleSpinBox()
        self.gain_spin.setDecimals(3)
        self.gain_spin.setRange(0.1, 1.0)
        self.gain_spin.setSingleStep(0.01)
        self.gain_spin.setValue(0.5)

        self.warp_amp_spin = QDoubleSpinBox()
        self.warp_amp_spin.setDecimals(3)
        self.warp_amp_spin.setRange(0.0, 1.0)
        self.warp_amp_spin.setSingleStep(0.01)
        self.warp_amp_spin.setValue(0.1)

        self.warp_freq_spin = QDoubleSpinBox()
        self.warp_freq_spin.setDecimals(3)
        self.warp_freq_spin.setRange(0.001, 0.1)
        self.warp_freq_spin.setSingleStep(0.001)
        self.warp_freq_spin.setValue(0.02)

        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 2**31 - 1)
        self.seed_spin.setValue(42)

        spinboxes = [
            self.base_freq_spin,
            self.octaves_spin,
            self.lacunarity_spin,
            self.gain_spin,
            self.warp_amp_spin,
            self.warp_freq_spin,
            self.seed_spin
        ]
        for sb in spinboxes:
            sb.setMaximumWidth(120)

        # place them in the grid
        add_control("Base Frequency:", self.base_freq_spin, 0)
        add_control("Octaves:",          self.octaves_spin, 1)
        add_control("Lacunarity:",      self.lacunarity_spin, 2)
        add_control("Gain:",            self.gain_spin, 3)
        add_control("Warp Amplitude:",  self.warp_amp_spin, 4)
        add_control("Warp Frequency:",  self.warp_freq_spin, 5)
        add_control("Seed:",            self.seed_spin, 6)

        # center the control grid and allow horizontal expansion
        control_container = QWidget()
        control_container.setLayout(control_layout)
        control_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        control_wrapper = QHBoxLayout()
        control_wrapper.addStretch(1)
        control_wrapper.addWidget(control_container)
        control_wrapper.addStretch(1)
        main_layout.addLayout(control_wrapper)

        # another stretcher so the “Continue” button stays at the bottom
        main_layout.addStretch(1)

        # === Continue button ===
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setAlignment(Qt.AlignCenter)
        self.next_button = QPushButton("Continue")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.next_button.setFont(font)
        self.next_button.setFixedSize(180, 45)
        btn_layout.addWidget(self.next_button)
        main_layout.addWidget(btn_container)

        # === Styling ===
        self.setStyleSheet("""
            QWidget {
                background-color: white;
            }
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
            QLabel {
                font-size: 13px;
            }
        """)

        # wire up preview updates
        for widget in spinboxes:
            widget.valueChanged.connect(self.update_preview)

    def apply_settings(self, config: dict):
        self.config = config
        self.seed_spin.setValue(config.get('seed', 42))
        self.update_preview()

    def update_preview(self):
        if not self.config:
            return
        self.generator = HeightmapGenerator(
            seed=self.seed_spin.value(),
            base_freq=self.base_freq_spin.value(),
            octaves=self.octaves_spin.value(),
            lacunarity=self.lacunarity_spin.value(),
            gain=self.gain_spin.value(),
            warp_amp=self.warp_amp_spin.value(),
            warp_freq=self.warp_freq_spin.value(),
        )
        w, h = self.preview_size
        img = self.generator.generate(w, h)
        self.preview_label.setPixmap(pillow_to_pixmap(img))

    def get_heightmap(self):
        if not self.generator or not self.config:
            return None
        width = self.config.get('width', self.preview_size[0])
        height = self.config.get('height', self.preview_size[1])
        return self.generator.generate(width, height)
