# -*- coding: utf-8 -*-
# ui/clipboard_pro.py

import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel)
from PyQt5.QtCore import Qt
from core.config import STYLES, COLORS
from data.db_manager import DatabaseManager

class ClipboardProWindow(QWidget):
    def __init__(self, context):
        super().__init__()
        self.context = context
        self.db = context.db_manager
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        self.setWindowTitle('Clipboard Pro')
        self.resize(400, 600)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setSpacing(0)

        # Container for background and border
        container = QWidget()
        container.setObjectName("container")
        container.setStyleSheet(f"""
            #container {{
                background-color: {COLORS['bg_dark']};
                border: 1px solid {COLORS['bg_light']};
                border-radius: 8px;
            }}
        """)
        main_layout.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Title bar
        title_bar = self._create_titlebar()
        layout.addWidget(title_bar)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("搜索剪贴板历史...")
        self.search_bar.setStyleSheet(STYLES['input'])
        self.search_bar.textChanged.connect(self._load_data)
        layout.addWidget(self.search_bar)

        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {COLORS['bg_light']};
                border-radius: 4px;
                background-color: {COLORS['bg_mid']};
            }}
            QListWidget::item {{
                padding: 8px;
                color: {COLORS['text']};
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['primary']};
                color: white;
            }}
        """)
        layout.addWidget(self.list_widget)

    def _create_titlebar(self):
        title_bar = QWidget()
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Clipboard Pro")
        title.setStyleSheet("font-weight: bold; color: #ccc;")
        layout.addWidget(title)
        layout.addStretch()

        # Placeholder for future buttons
        pin_btn = QLabel("📌")
        layout.addWidget(pin_btn)

        eye_btn = QLabel("👁️")
        eye_btn.setCursor(Qt.PointingHandCursor)
        eye_btn.mousePressEvent = self.open_main_window
        layout.addWidget(eye_btn)

        min_btn = QLabel("─")
        layout.addWidget(min_btn)

        close_btn = QLabel("✕")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.mousePressEvent = lambda e: self.close()
        layout.addWidget(close_btn)

        return title_bar

    def open_main_window(self, event):
        self.context.show_main_window()

    def _load_data(self):
        self.list_widget.clear()
        search_term = self.search_bar.text()

        # Using the existing get_ideas method for now
        ideas = self.db.get_ideas(search_term, 'all', None)

        for idea in ideas:
            # id, title, content, color, is_pinned, is_favorite, created_at, is_deleted
            title = idea[1]
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, idea[0]) # Store idea id
            self.list_widget.addItem(item)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(e.globalPos() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
