# File: export_widget.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QPushButton

class ExportWidget(QWidget):
    """The fifth and final page for viewing and exporting the result."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Scroll area is crucial for large images
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.image_label)
        
        self.export_button = QPushButton("Export to PNG...")
        
        layout.addWidget(scroll_area, stretch=1)
        layout.addWidget(self.export_button)

        self.final_pixmap = None # To hold a reference for saving

    def set_final_image(self, pixmap):
        self.final_pixmap = pixmap
        self.image_label.setPixmap(self.final_pixmap)