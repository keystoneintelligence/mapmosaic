# File: main_window.py
import os
from datetime import datetime

from PySide6.QtWidgets import QMainWindow, QStackedWidget, QFileDialog
from PySide6.QtGui import QPixmap, QImage
from PIL import Image
from PIL.ImageQt import ImageQt

# Import all the page widgets
from gui.setup_widget import SetupWidget
from gui.editor_widget import EditorWidget
from gui.grid_widget import GridWidget
from gui.generator_widget import GeneratorWidget
from gui.export_widget import ExportWidget

from noise.heightmap_generator import HeightmapGenerator
from noise.terrain_generator import TerrainGenerator

from inference.openai import OpenAIImageGenerator

def pillow_to_pixmap(img: Image.Image) -> QPixmap:
    """Converts a Pillow Image to a PySide6 QPixmap."""
    if img.mode == "RGB":
        # The call to Image.merge() is now correct because 'Image' is the module.
        qimage = QImage(img.tobytes(), img.width, img.height, QImage.Format.Format_RGB888)
    elif img.mode == "RGBA":
        qimage = QImage(img.tobytes(), img.width, img.height, QImage.Format.Format_ARGB32)
    elif img.mode == "L": # Greyscale
        qimage = QImage(img.tobytes(), img.width, img.height, img.width, QImage.Format.Format_Grayscale8)
    else: # Fallback
        rgb_img = img.convert("RGB")
        qimage = QImage(rgb_img.tobytes(), rgb_img.width, rgb_img.height, QImage.Format.Format_RGB888)

    return QPixmap.fromImage(qimage)


class MainWindow(QMainWindow):
    """The main application window that orchestrates the workflow."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Map Mosaic")
        self.setGeometry(100, 100, 800, 650)

        self.output_fpath = make_timestamped_dir()
        
        self.project_data = {}
        self.heightmap_pixmap = None
        self.colormap_pixmap = None

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.setup_page = SetupWidget()
        self.editor_page = EditorWidget()
        self.grid_page = GridWidget(output_fpath=self.output_fpath)
        self.generator_page = GeneratorWidget(output_fpath=self.output_fpath)
        self.export_page = ExportWidget()
        
        self.stacked_widget.addWidget(self.setup_page)
        self.stacked_widget.addWidget(self.editor_page)
        self.stacked_widget.addWidget(self.grid_page)
        self.stacked_widget.addWidget(self.generator_page)
        self.stacked_widget.addWidget(self.export_page)

        self.setup_page.next_button.clicked.connect(self.go_to_editor)
        self.editor_page.next_button.clicked.connect(self.go_to_grid)
        self.grid_page.next_button.clicked.connect(self.go_to_generator)
        self.generator_page.next_button.clicked.connect(self.go_to_export)
        self.export_page.export_button.clicked.connect(self.export_image)

    def go_to_editor(self):
        # 1. Gather data from the setup page
        self.project_data['name'] = self.setup_page.name_input.text()
        self.project_data['filename'] = self.setup_page.filename_input.text()
        self.project_data['description'] = self.setup_page.description_input.toPlainText()
        self.project_data['openai_api_key'] = self.setup_page.api_key_input.text()
        self.project_data['seed'] = int(self.setup_page.seed_input.text())
        width = self.setup_page.width_input.value()
        height = self.setup_page.height_input.value()
        self.project_data['size'] = (width, height)

        self.image_generator = OpenAIImageGenerator(self.project_data['openai_api_key'])
        self.image_generator.test_api_key()

        # 2. Prepare data for the editor page
        self.create_initial_maps(512, 512, self.project_data['seed'])
        self.editor_page.set_maps(self.heightmap_pixmap, self.colormap_pixmap)
        
        # 3. Transition
        self.stacked_widget.setCurrentIndex(1)
        
    def go_to_grid(self):
        #self.generate_rough_draft_and_replace_colormap()
        self.grid_page.set_grid_images(self.image_generator, self.colormap_pixmap, self.project_data['description'])
        self.stacked_widget.setCurrentIndex(2)
        
    def go_to_generator(self):
        self.generator_page.generate(
            self.grid_page.selected_path,
            self.project_data['size'][0],
            self.grid_page.corner,
            self.colormap_pixmap,
            self.image_generator,
            self.project_data['description'],
        )
        self.stacked_widget.setCurrentIndex(3)

    def go_to_export(self):
        self.export_page.set_final_image(QPixmap.fromImage(ImageQt(self.generator_page.current_nomap)))
        self.stacked_widget.setCurrentIndex(4)

    def create_initial_maps(self, width, height, seed=1337):
        """Generates initial maps using the noise libraries."""
        print(f"Generating maps ({width}x{height}) with seed: {seed}")
        
        hm_gen = HeightmapGenerator(seed=seed,
                                    base_freq=0.003,
                                    octaves=7,
                                    lacunarity=2.0,
                                    gain=0.4,
                                    warp_amp=0.15,
                                    warp_freq=0.02)
        heightmap_pillow = hm_gen.generate(width, height)
        terrain_pillow = TerrainGenerator().apply(heightmap_pillow)

        self.heightmap_pixmap = pillow_to_pixmap(heightmap_pillow)
        self.colormap_pixmap = pillow_to_pixmap(terrain_pillow)
        
        print("Map generation complete.")

    def generate_rough_draft_and_replace_colormap(self):
        """Generate a rough draft from the colormap, upscale to 1024x1024, and replace the current colormap_pixmap."""
        # Save temporary colormap image
        rough_ref_path = os.path.join(self.output_fpath, "intermediate_colormap_reference.png")
        self.colormap_pixmap.save(rough_ref_path, "PNG")

        # Generate rough draft image using OpenAI
        rough_draft_path = self.image_generator.generate_rough_draft_image(
            working_dir=self.output_fpath,
            reference_image=rough_ref_path,
            map_description=self.project_data["description"]
        )

        if not rough_draft_path:
            raise RuntimeError("Failed to generate rough draft image.")

        # Replace colormap_pixmap with resized result
        self.colormap_pixmap = QPixmap(rough_draft_path)

    def export_image(self):
        default_filename = self.project_data.get('filename', 'map_export').split('.')[0] + ".png"
        
        filePath, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Image", 
            default_filename,
            "PNG Files (*.png);;All Files (*)"
        )
        
        if filePath:
            if not self.export_page.final_pixmap.save(filePath, "PNG"):
                print(f"Error: Could not save file to {filePath}")
            else:
                print(f"File saved successfully to {filePath}")


def make_timestamped_dir(base_path: str = "./output") -> str:
    """
    Create a new folder named with the current timestamp under base_path.
    Returns the full path to the created directory.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_path = os.path.join(base_path, timestamp)
    os.makedirs(dir_path, exist_ok=True)
    return dir_path
