# File: main.py
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui", "favicon.png")
    app.setWindowIcon(QIcon(logo_path))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())