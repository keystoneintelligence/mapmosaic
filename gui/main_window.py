import os
from datetime import datetime
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMainWindow, QStackedWidget

# Import workflow widgets
from gui.welcome_widget import WelcomeWidget
from gui.noise_widget import NoiseWidget
from gui.feature_mapping_widget import FeatureMappingWidget
from gui.final_render_widget import FinalRenderWidget

# OpenAI image generator
from inference.openai import OpenAIImageGenerator


def make_timestamped_dir(base_path: str = "./output") -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_path = os.path.join(base_path, timestamp)
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MapMosaic")

        # Prepare output directory
        self.output_dir = make_timestamped_dir()

        # Load API key
        key_path = "./api.key"
        if not os.path.exists(key_path):
            raise FileNotFoundError("OpenAI Key should be in ./api.key")
        with open(key_path, "r") as f:
            api_key = f.read().strip()

        # Initialize OpenAI generator
        self.image_generator = OpenAIImageGenerator(api_key=api_key)

        # Set up stacked workflow
        self.stacked_widget = QStackedWidget()
        # Force entire window background to white
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("white"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        self.setCentralWidget(self.stacked_widget)

        # Instantiate pages
        self.welcome_page = WelcomeWidget()
        self.noise_page = NoiseWidget()
        self.feature_page = FeatureMappingWidget()
        self.final_page = FinalRenderWidget(generator=self.image_generator)

        # Add pages in order
        for page in (self.welcome_page, self.noise_page, self.feature_page, self.final_page):
            self.stacked_widget.addWidget(page)

        # Navigation connections
        self.welcome_page.start_button.clicked.connect(self.go_to_noise)
        self.noise_page.next_button.clicked.connect(self.go_to_feature)
        self.feature_page.back_button.clicked.connect(self.go_to_noise)
        self.feature_page.next_button.clicked.connect(self.go_to_final)
        self.final_page.back_button.clicked.connect(self.go_to_feature)

        # Default screen is the welcome page
        self.stacked_widget.setCurrentWidget(self.welcome_page)

    def go_to_noise(self):
        default_cfg = {
            'seed': 42,
            'width': self.noise_page.preview_size[0],
            'height': self.noise_page.preview_size[1]
        }
        self.noise_page.apply_settings(default_cfg)
        self.stacked_widget.setCurrentWidget(self.noise_page)

    def go_to_feature(self):
        heightmap = self.noise_page.get_heightmap()
        if heightmap:
            heightmap.save(os.path.join(self.output_dir, "heightmap.png"))
            self.feature_page.set_heightmap(heightmap)
        self.stacked_widget.setCurrentWidget(self.feature_page)

    def go_to_final(self):
        colormap = self.feature_page.get_colormap()
        feat_path = os.path.join(self.output_dir, "featuremap.png")
        if hasattr(colormap, 'save'):
            colormap.save(feat_path)
        else:
            colormap.save(feat_path, "PNG")
        self.final_page.output_dir = self.output_dir
        self.final_page.set_colormap(colormap)
        self.stacked_widget.setCurrentWidget(self.final_page)
