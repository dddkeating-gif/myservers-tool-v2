# This Python file uses the following encoding: utf-8
"""V2 entrypoint: PySide6 + MainWindow from myservers.ui.main_window."""
import sys
from PySide6.QtWidgets import QApplication
from myservers.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(900, 600)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
