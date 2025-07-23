# File: setup_widget.py
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QTextEdit, 
    QSpinBox, QPushButton, QHBoxLayout, QLabel
)

DEFAULT_SIZE = 2048  # 8192

class SetupWidget(QWidget):
    """The first page of the workflow for setting up the project."""
    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self.name_input = QLineEdit("My Awesome Map")
        self.filename_input = QLineEdit("my_awesome_map.mosaic")
        self.description_input = QTextEdit("A description of the map goes here.")
        self.seed_input = QLineEdit()
        self.seed_input.setValidator(QIntValidator(0, 2**31 - 1))  # Accepts only integers in range
        self.seed_input.setText("1337")  # Set default value
        self.api_key_input = QLineEdit("OpenAI API Key Goes Here")
        
        size_layout = QHBoxLayout()
        self.width_input = QSpinBox()
        self.width_input.setRange(DEFAULT_SIZE, DEFAULT_SIZE)
        self.width_input.setValue(DEFAULT_SIZE)
        self.height_input = QSpinBox()
        self.height_input.setRange(DEFAULT_SIZE, DEFAULT_SIZE)
        self.height_input.setValue(DEFAULT_SIZE)
        size_layout.addWidget(QLabel("Width:"))
        size_layout.addWidget(self.width_input)
        size_layout.addWidget(QLabel("Height:"))
        size_layout.addWidget(self.height_input)

        self.next_button = QPushButton("Continue")
        
        layout.addRow("Project Name:", self.name_input)
        layout.addRow("Filename:", self.filename_input)
        layout.addRow("Description:", self.description_input)
        layout.addRow("Size (pixels):", size_layout)
        layout.addRow("Seed:", self.seed_input)
        layout.addRow("OpenAI API Key:", self.api_key_input)
        layout.addRow(self.next_button)