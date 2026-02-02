# This Python file uses the following encoding: utf-8
"""Thin UI: MainWindow for v2. Business logic lives in myservers/core; storage in myservers/storage."""
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel


class MainWindow(QMainWindow):
    """Minimal v2 main window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MyServers")
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(QLabel("MyServers v2"))
        self.setCentralWidget(central)
