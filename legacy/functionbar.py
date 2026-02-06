# This Python file uses the following encoding: utf-8
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton


class FunctionBar(QFrame):
    button_clicked = Signal(str)

    def __init__(self, labels) -> None:
        super().__init__()
        self.setObjectName("functionBar")
        self.setFixedHeight(36)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 4, 12, 4)
        self._layout.setSpacing(8)
        self._layout.addStretch()
        self._buttons = {}
        self.set_buttons(labels)

    def set_buttons(self, labels) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._buttons.clear()
        for item in labels:
            if isinstance(item, tuple):
                label, action_id = item
            else:
                label = item
                action_id = str(item).lower()
            button = QPushButton(label)
            button.setObjectName("functionButton")
            if callable(action_id):
                button.clicked.connect(lambda _=False, fn=action_id: fn())
            else:
                button.clicked.connect(lambda _, action=action_id: self.button_clicked.emit(action))
            self._layout.insertWidget(self._layout.count() - 1, button)
            self._buttons[action_id] = button
