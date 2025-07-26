from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGridLayout, QDoubleSpinBox,
    QSpinBox, QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PIL.ImageQt import ImageQt

from noise.heightmap_generator import HeightmapGenerator


def pillow_to_pixmap(img):
    """Convert a PIL Image to QPixmap via ImageQt."""
    qimage = ImageQt(img.convert("RGBA"))
    return QPixmap.fromImage(qimage)


class NoiseWidget(QWidget):
    """
    Widget for tuning noise parameters and previewing the generated heightmap.
    """
    def __init__(self):
        super().__init__()
        self.config = None
        self.generator = None
        self.preview_size = (512, 512)

        # Layouts
        main_layout = QVBoxLayout(self)
        control_layout = QGridLayout()

        # Preview label
        self.preview_label = QLabel(alignment=Qt.AlignCenter)
        self.preview_label.setFixedSize(*self.preview_size)
        main_layout.addWidget(self.preview_label)

        # Noise parameter controls
        # Base frequency
        control_layout.addWidget(QLabel("Base Frequency:"), 0, 0)
        self.base_freq_spin = QDoubleSpinBox()
        self.base_freq_spin.setRange(0.0001, 0.1)
        self.base_freq_spin.setSingleStep(0.0001)
        self.base_freq_spin.setValue(0.005)
        control_layout.addWidget(self.base_freq_spin, 0, 1)

        # Octaves
        control_layout.addWidget(QLabel("Octaves:"), 1, 0)
        self.octaves_spin = QSpinBox()
        self.octaves_spin.setRange(1, 10)
        self.octaves_spin.setValue(6)
        control_layout.addWidget(self.octaves_spin, 1, 1)

        # Lacunarity
        control_layout.addWidget(QLabel("Lacunarity:"), 2, 0)
        self.lacunarity_spin = QDoubleSpinBox()
        self.lacunarity_spin.setRange(1.0, 4.0)
        self.lacunarity_spin.setSingleStep(0.1)
        self.lacunarity_spin.setValue(2.2)
        control_layout.addWidget(self.lacunarity_spin, 2, 1)

        # Gain
        control_layout.addWidget(QLabel("Gain:"), 3, 0)
        self.gain_spin = QDoubleSpinBox()
        self.gain_spin.setRange(0.1, 1.0)
        self.gain_spin.setSingleStep(0.01)
        self.gain_spin.setValue(0.5)
        control_layout.addWidget(self.gain_spin, 3, 1)

        # Warp Amplitude
        control_layout.addWidget(QLabel("Warp Amplitude:"), 4, 0)
        self.warp_amp_spin = QDoubleSpinBox()
        self.warp_amp_spin.setRange(0.0, 1.0)
        self.warp_amp_spin.setSingleStep(0.01)
        self.warp_amp_spin.setValue(0.1)
        control_layout.addWidget(self.warp_amp_spin, 4, 1)

        # Warp Frequency
        control_layout.addWidget(QLabel("Warp Frequency:"), 5, 0)
        self.warp_freq_spin = QDoubleSpinBox()
        self.warp_freq_spin.setRange(0.001, 0.1)
        self.warp_freq_spin.setSingleStep(0.001)
        self.warp_freq_spin.setValue(0.02)
        control_layout.addWidget(self.warp_freq_spin, 5, 1)

        # Seed
        control_layout.addWidget(QLabel("Seed:"), 6, 0)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 2**31 - 1)
        self.seed_spin.setValue(42)
        control_layout.addWidget(self.seed_spin, 6, 1)

        main_layout.addLayout(control_layout)

        # Navigation buttons
        btn_layout = QHBoxLayout()
        self.next_button = QPushButton("Continue")
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.next_button)
        main_layout.addLayout(btn_layout)

        # Connect update on value change
        for widget in (
            self.base_freq_spin,
            self.octaves_spin,
            self.lacunarity_spin,
            self.gain_spin,
            self.warp_amp_spin,
            self.warp_freq_spin,
            self.seed_spin,
        ):
            widget.valueChanged.connect(self.update_preview)

    def apply_settings(self, config: dict):
        """
        Receive settings from SetupWidget (e.g. width, height).
        Initialize the noise generator and render initial preview.
        """
        self.config = config
        # Set seed control from config
        self.seed_spin.setValue(config.get('seed', 42))
        # Initial preview
        self.update_preview()

    def update_preview(self):
        """
        Generate a low-resolution heightmap and display it.
        """
        if not self.config:
            return
        # Create a new generator on each update to honor seed changes
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
        pix = pillow_to_pixmap(img)
        self.preview_label.setPixmap(pix)

    def get_heightmap(self):
        """
        Generate and return the full-resolution heightmap as a PIL Image.
        """
        if not self.generator or not self.config:
            return None
        width = self.config.get('width', self.preview_size[0])
        height = self.config.get('height', self.preview_size[1])
        return self.generator.generate(width, height)
