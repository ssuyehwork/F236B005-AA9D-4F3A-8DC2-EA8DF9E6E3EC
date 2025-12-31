# ui/preview_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QTextEdit, QWidget, QDesktopWidget)
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtCore import Qt

from core.config import COLORS

# 滚动条样式是从 dialogs.py 复制过来的，因为它被文本预览使用
SCROLLBAR_STYLE = """
QScrollBar:vertical {
    border: none;
    background: #222222;
    width: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #555555;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #666666;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""

class PreviewDialog(QDialog):
    def __init__(self, item_type, data, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._init_ui(item_type, data)

    def keyPressEvent(self, event):
        """重写 keyPressEvent 来处理按键关闭事件, 更加健壮"""
        if event.key() == Qt.Key_Escape or event.key() == Qt.Key_Space:
            self.close()
        else:
            super().keyPressEvent(event)

    def _init_ui(self, item_type, data):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setStyleSheet(f"background-color: {COLORS['bg_dark']}; border: 2px solid {COLORS['bg_mid']}; border-radius: 12px;")
        container_layout = QVBoxLayout(container)
        main_layout.addWidget(container)

        if item_type == 'text':
            self._setup_text_preview(container_layout, data)
        elif item_type == 'image':
            self._setup_image_preview(container_layout, data)

    def _setup_text_preview(self, layout, text_data):
        self.resize(600, 500)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setText(text_data)
        text_edit.setStyleSheet(f"QTextEdit {{ background-color: transparent; border: none; padding: 15px; color: #ddd; font-size: 14px; }} {SCROLLBAR_STYLE}")
        layout.addWidget(text_edit)

    def _setup_image_preview(self, layout, image_data):
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)

        if pixmap.isNull():
            label = QLabel("无法加载图片")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #E81123; font-size: 16px;")
            layout.addWidget(label)
            self.resize(300, 200)
            return

        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        screen_geo = QDesktopWidget().availableGeometry(self)
        max_width = screen_geo.width() * 0.8
        max_height = screen_geo.height() * 0.8

        scaled_pixmap = pixmap.scaled(int(max_width), int(max_height), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled_pixmap)

        self.resize(scaled_pixmap.width() + 20, scaled_pixmap.height() + 20)

    def mousePressEvent(self, event):
        self.close()
