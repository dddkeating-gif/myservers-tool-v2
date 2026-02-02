# This Python file uses the following encoding: utf-8
# python3 -m unittest tests.py
import os
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMessageBox

from main import MainWindow


class MainPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()


## _call_MainPage Tests
    def test_call_main_page_by_name(self) -> None:
        expected_index = self.window._get_page_info(entry="ServerHome", get_NameIndex=True)
        self.window._call_MainPage("ServerHome")
        self.assertEqual(self.window._stack.currentIndex(), expected_index)

    def test_call_main_page_by_index_string(self) -> None:
        self.window._call_MainPage("4")
        self.assertEqual(self.window._stack.currentIndex(), 4)

    def test_confirm_delete_true_false(self) -> None:
        with patch("main.QMessageBox.question", return_value=QMessageBox.Yes):
            self.assertTrue(self.window._confirm_delete("ServerA"))
        with patch("main.QMessageBox.question", return_value=QMessageBox.No):
            self.assertFalse(self.window._confirm_delete("ServerA"))

    def test_confirm_delete_empty_name(self) -> None:
        with patch("main.QMessageBox.question") as mocked:
            self.assertFalse(self.window._confirm_delete(""))
            mocked.assert_not_called()

    def test_get_payload_servers(self) -> None:
        self.window._server_InternalPrimaryHost_value = "10.0.0.1"
        self.window._server_InternalSecondaryHost_value = "10.0.0.2"
        self.window._server_ExternalPrimaryHost_value = "203.0.113.1"
        self.window._server_ExternalSecondaryHost_value = "203.0.113.2"
        payload = self.window._get_payload("Servers", "Test", "uuid-123")
        self.assertIn("uuid-123", payload)
        self.assertEqual(payload["Hosts"]["Internal_Primary"], "10.0.0.1")
        self.assertEqual(payload["Hosts"]["External_Secondary"], "203.0.113.2")

    def test_get_page_info(self) -> None:
        self.assertEqual(self.window._get_page_info(entry="Settings", get_NameIndex=True), 4)
        self.assertEqual(self.window._get_page_info(entry=0, get_IndexName=True), "Home")
        self.assertEqual(self.window._get_page_info(entry=2, get_Functions=True), [("Save", "servers.save"), ("Cancel", "servers.cancel")])
