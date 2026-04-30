from __future__ import annotations
import sys
import win32gui
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QMessageBox,
    QSystemTrayIcon, QMenu,
)
from overlay import OverlayWindow
from settings import AppSettings
from settings_dialog import SettingsDialog


def _enum_callback(hwnd: int, result: list) -> bool:
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if title:
            result.append((hwnd, title))
    return True


def get_visible_windows() -> list[tuple[int, str]]:
    windows: list[tuple[int, str]] = []
    win32gui.EnumWindows(_enum_callback, windows)
    return sorted(windows, key=lambda x: x[1].lower())


def _make_tray_icon() -> QIcon:
    """オレンジ円に「N」の文字を描いたトレイアイコンを生成する。"""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(255, 140, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 28, 28)
    font = QFont("Yu Gothic UI", 14)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "N")
    painter.end()
    return QIcon(pixmap)


class WindowSelectDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("niconico_inspire_comment (local) — ウィンドウを選択")
        self.setMinimumSize(520, 420)
        self.selected_hwnd: int | None = None
        self.selected_title: str = ""

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("コメントを流したいウィンドウを選択してください:"))

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        self._btn_ok     = QPushButton("開始")
        self._btn_cancel = QPushButton("キャンセル")
        self._btn_ok.setDefault(True)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_ok)
        btn_row.addWidget(self._btn_cancel)
        layout.addLayout(btn_row)

        self._btn_ok.clicked.connect(self._on_ok)
        self._btn_cancel.clicked.connect(self.reject)
        self._list.itemDoubleClicked.connect(self._on_ok)

        self._populate()

    def _populate(self) -> None:
        for hwnd, title in get_visible_windows():
            item = QListWidgetItem(f"{title}  [HWND: {hwnd}]")
            item.setData(Qt.ItemDataRole.UserRole, hwnd)
            item.setData(Qt.ItemDataRole.UserRole + 1, title)
            self._list.addItem(item)

    def _on_ok(self) -> None:
        item = self._list.currentItem()
        if item is None:
            QMessageBox.warning(self, "選択エラー", "ウィンドウを選択してください。")
            return
        self.selected_hwnd  = item.data(Qt.ItemDataRole.UserRole)
        self.selected_title = item.data(Qt.ItemDataRole.UserRole + 1)
        self.accept()


def main() -> None:
    app = QApplication(sys.argv)
    # トレイアイコンでアプリを管理するため、ウィンドウが全て閉じても終了しない
    app.setQuitOnLastWindowClosed(False)

    dialog = WindowSelectDialog()
    if dialog.exec() != QDialog.DialogCode.Accepted or dialog.selected_hwnd is None:
        sys.exit(0)

    settings = AppSettings.load()
    overlay = OverlayWindow(dialog.selected_hwnd, settings)
    overlay.show()

    # --- システムトレイアイコン ---
    tray = QSystemTrayIcon(_make_tray_icon(), app)
    tray.setToolTip(f"niconico_inspire_comment (local)\n対象: {dialog.selected_title}")

    menu = QMenu()

    target_action = QAction(f"対象: {dialog.selected_title}")
    target_action.setEnabled(False)
    menu.addAction(target_action)
    menu.addSeparator()

    settings_action = QAction("設定...")
    settings_action.triggered.connect(lambda: _show_settings_dialog(overlay))
    menu.addAction(settings_action)
    menu.addSeparator()

    quit_action = QAction("終了")
    quit_action.triggered.connect(lambda: _shutdown(app, overlay, tray))
    menu.addAction(quit_action)

    tray.setContextMenu(menu)

    # ダブルクリックでも終了できる
    tray.activated.connect(
        lambda reason: _shutdown(app, overlay, tray)
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick
        else None
    )

    tray.show()
    tray.showMessage(
        "niconico_inspire_comment (local) 起動中",
        "終了するにはタスクトレイのアイコンを右クリック → 「終了」",
        QSystemTrayIcon.MessageIcon.Information,
        4000,
    )

    sys.exit(app.exec())


def _shutdown(app: QApplication, overlay: OverlayWindow, tray: QSystemTrayIcon) -> None:
    tray.hide()
    overlay.close()
    app.quit()


def _show_settings_dialog(overlay: OverlayWindow) -> None:
    dialog = SettingsDialog(overlay.settings())
    dialog.settings_applied.connect(overlay.apply_settings)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        settings = dialog.current_settings()
        settings.save()
        overlay.apply_settings(settings)


if __name__ == "__main__":
    main()
