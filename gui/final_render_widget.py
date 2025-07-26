import os
from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QHBoxLayout, QTextEdit, QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QPixmap, QFont, QPalette, QColor


def pillow_to_pixmap(img):
    """Convert a PIL Image to QPixmap via ImageQt."""
    qimage = ImageQt(img.convert("RGBA"))
    return QPixmap.fromImage(qimage)


class _RenderWorker(QObject):
    """Worker to run the OpenAI API call in a separate thread."""
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, generator, base_image, prompt):
        super().__init__()
        self.generator = generator
        self.base_image = base_image
        self.prompt = prompt

    def run(self):
        try:
            result = self.generator.generate_rough_draft_image(
                working_dir=self.base_image['working_dir'],
                reference_image=self.base_image['path'],
                map_description=self.prompt
            )
            img = Image.open(result)
            self.finished.emit(img)
        except Exception as e:
            self.error.emit(str(e))


class FinalRenderWidget(QWidget):
    """
    Widget to accept a colormap, style prompt, and generate a rough-draft map via OpenAI,
    showing progress, result, and export capability.
    """
    def __init__(self, generator):
        super().__init__()
        # === Force white background ===
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("white"))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        self.generator = generator
        self.original_pixmap = None
        self.output_dir = None

        # === Main layout ===
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(25)

        # Preview label
        self.preview_label = QLabel("No map loaded.")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.preview_label, stretch=1)

        # API Key input
        key_layout = QHBoxLayout()
        key_layout.setAlignment(Qt.AlignCenter)
        key_layout.addWidget(QLabel("OpenAI API Key:"))
        self.api_key_input = QLineEdit()
        key_file = "./api.key"
        if os.path.exists(key_file):
            try:
                with open(key_file, "r") as f:
                    self.api_key_input.setText(f.read().strip())
            except IOError:
                pass
        key_layout.addWidget(self.api_key_input)
        main_layout.addLayout(key_layout)

        # Prompt input
        prompt_label = QLabel("Art Style Prompt:")
        prompt_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(prompt_label)
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(
            "Describe the artistic style or details (e.g., 'ancient hand-drawn fantasy map with muted earth tones')"
        )
        self.prompt_input.setFixedHeight(80)
        main_layout.addWidget(self.prompt_input)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        self.back_button = QPushButton("Back")
        self.generate_button = QPushButton("Generate")
        self.export_button = QPushButton("Export")
        self.export_button.setEnabled(False)
        btn_layout.addWidget(self.back_button)
        btn_layout.addSpacing(20)
        btn_layout.addWidget(self.generate_button)
        btn_layout.addWidget(self.export_button)
        main_layout.addLayout(btn_layout)

        # === Style control buttons ===
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        style = """
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
        for btn in (self.back_button, self.generate_button, self.export_button):
            btn.setFont(font)
            btn.setFixedHeight(45)
            btn.setStyleSheet(style)

        # Connections
        self.generate_button.clicked.connect(self.start_generation)
        self.export_button.clicked.connect(self.save_final_map)

    def set_colormap(self, colormap_image):
        """Receive a PIL.Image or QPixmap, save for AI input, and display."""
        from PIL import Image
        # Convert QPixmap to PIL if needed
        if isinstance(colormap_image, QPixmap):
            qimg = colormap_image.toImage()
            img = ImageQt(qimg)
        else:
            img = colormap_image

        # Save base for AI
        if not self.output_dir:
            raise RuntimeError("output_dir must be set before set_colormap")
        base_path = os.path.join(self.output_dir, "featuremap.png")
        img.save(base_path)

        # Set up for worker
        self.base_image = {'path': base_path, 'working_dir': self.output_dir}

        # Display
        pix = pillow_to_pixmap(img)
        self._update_preview(pix)
        self.export_button.setEnabled(False)

    def start_generation(self):
        # Save API key to file
        key = self.api_key_input.text().strip()
        if key:
            try:
                with open("./api.key", "w") as f:
                    f.write(key)
            except IOError:
                pass
            if hasattr(self.generator, 'api_key'):
                self.generator.api_key = key

        prompt = self.prompt_input.toPlainText().strip()
        if not prompt or not hasattr(self, 'base_image'):
            return

        self.generate_button.setEnabled(False)
        self.back_button.setEnabled(False)
        self.progress_bar.setVisible(True)

        self.thread = QThread()
        self.worker = _RenderWorker(self.generator, self.base_image, prompt)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_render_finished)
        self.worker.error.connect(self.on_render_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.thread.start()

    def on_render_finished(self, result_image):
        pix = pillow_to_pixmap(result_image)
        self.original_pixmap = pix
        self._update_preview(pix)
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        self.back_button.setEnabled(True)
        self.export_button.setEnabled(True)

    def on_render_error(self, errmsg):
        self.preview_label.setText(f"Error generating map:\n{errmsg}")
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        self.back_button.setEnabled(True)

    def _update_preview(self, pixmap: QPixmap):
        """Scale and set pixmap to fit current label size."""
        self.original_pixmap = pixmap
        label_size = self.preview_label.size()
        if not label_size.isEmpty():
            scaled = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled)
        else:
            self.preview_label.setPixmap(pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.original_pixmap:
            self._update_preview(self.original_pixmap)

    def get_final_pixmap(self) -> QPixmap:
        return self.original_pixmap

    def save_final_map(self):
        """Save the generated map to disk in output_dir."""
        if self.original_pixmap and self.output_dir:
            path = os.path.join(self.output_dir, "roughdraft.png")
            self.original_pixmap.save(path, "PNG")
