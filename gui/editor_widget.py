# File: editor_widget.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
    QPushButton, QSpinBox, QColorDialog
)
from PySide6.QtCore import Qt
from gui.paintable_label import PaintableLabel

class EditorWidget(QWidget):
    """The second page of the workflow for editing the map layers."""
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        self.layer_combo = QComboBox()
        self.layer_combo.addItems(["Greyscale Heightmap", "Colorized Terrain Map"])
        self.layer_combo.setCurrentIndex(1)

        self.color_button = QPushButton("Pick Color")
        self.brush_size_input = QSpinBox()
        self.brush_size_input.setRange(1, 100)
        self.brush_size_input.setValue(10)
        self.brush_size_input.setPrefix("Brush Size: ")
        
        toolbar_layout.addWidget(self.layer_combo)
        toolbar_layout.addWidget(self.color_button)
        toolbar_layout.addWidget(self.brush_size_input)
        toolbar_layout.addStretch()
        
        # The canvas for painting
        self.canvas = PaintableLabel()
        self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas.setStyleSheet("border: 1px solid black;")

        self.next_button = QPushButton("Continue to Grid View")

        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.canvas, stretch=1)
        main_layout.addWidget(self.next_button, alignment=Qt.AlignmentFlag.AlignRight)
        
        # Connect internal signals
        self.color_button.clicked.connect(self.pick_color)
        self.brush_size_input.valueChanged.connect(self.update_brush_size)
        
        self.pixmaps = {} # To hold our two map images

    def set_maps(self, heightmap, colormap):
        self.pixmaps["Greyscale Heightmap"] = heightmap
        self.pixmaps["Colorized Terrain Map"] = colormap
        # Disconnect first to prevent multiple connections if this is called more than once
        try:
            self.layer_combo.currentIndexChanged.disconnect()
        except RuntimeError:
            pass # No connection existed yet
        self.layer_combo.currentIndexChanged.connect(self.switch_layer)
        self.switch_layer(1)

    def switch_layer(self, index):
        layer_name = self.layer_combo.itemText(index)
        active_pixmap = self.pixmaps.get(layer_name)
        if active_pixmap:
            self.canvas.set_active_pixmap(active_pixmap)

    def pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.canvas.brush_color = color
            self.color_button.setStyleSheet(f"background-color: {color.name()};")

    def update_brush_size(self, value):
        self.canvas.brush_size = value