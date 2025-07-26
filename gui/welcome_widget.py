import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QSizePolicy, QHBoxLayout
)
from PySide6.QtGui import QPixmap, QFont, QPalette, QColor
from PySide6.QtCore import Qt


class WelcomeWidget(QWidget):
    """Welcome screen with logo and introduction to MapMosaic."""
    def __init__(self):
        super().__init__()

        # === Force full white background ===
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("white"))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        # === Layout setup ===
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        # === Logo ===
        self.logo_label = QLabel()
        self.logo_label.setContentsMargins(0, 0, 0, 0)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setFrameShape(QLabel.NoFrame)
        self.logo_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.logo_label.setStyleSheet("""
            background: white;
            border: 12px solid #ffffff;
            padding: 0px;
            margin: 0px;
        """)
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "favicon.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)

        layout.addWidget(self.logo_label)

        # === Title and description ===
        self.welcome_text = QLabel()
        self.welcome_text.setTextFormat(Qt.TextFormat.RichText)
        self.welcome_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.welcome_text.setWordWrap(True)
        self.welcome_text.setText(
            "<div style='text-align:center;'>"
            "<h2 style='margin-bottom: 0.2em;'>Welcome to <span style='color:#5c4d7d;'>MapMosaic</span></h2>"
            "<p style='font-size: 1.05em; margin-top: 0;'>"
            "Create procedural, seamless, sylized maps using <b>AI</b>."
            "</p></div>"
        )
        layout.addWidget(self.welcome_text)

        # === Start Button Centered in its own layout ===
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.start_button = QPushButton("🗺️  Get Started")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.start_button.setFont(font)
        self.start_button.setFixedSize(180, 45)
        button_layout.addWidget(self.start_button)
        layout.addWidget(button_container)

        # === Apply stylesheet ===
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
        """)
