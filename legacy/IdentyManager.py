# This Python file uses the following encoding: utf-8
import sys
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget


class IdentityManagerWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Identity Manager")
        self.resize(700, 480)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QLabel("Identity Manager")
        header.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(header)
        layout.addStretch()

        self.setCentralWidget(central)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IdentityManagerWindow()
    window.show()
    sys.exit(app.exec())
