# -*- coding: utf-8 -*-
# ui/action_popup.py
import os
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QPushButton, QLabel, QGraphicsDropShadowEffect, QVBoxLayout, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint, QSize
from PyQt5.QtGui import QCursor, QColor, QPixmap
from core.config import COLORS
from ui.common_tags import CommonTags

class ActionPopup(QWidget):
    """
    复制成功后在鼠标附近弹出的快捷操作条
    布局逻辑： [大 Logo] | [收藏] [常用标签...] [管理]
    """
    request_favorite = pyqtSignal(int)
    request_tag_toggle = pyqtSignal(int, str, bool)
    request_manager = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_idea_id = None
        self.is_favorited = False

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._init_ui()

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._animate_hide)

    def _init_ui(self):
        # 主容器
        self.container = QWidget(self)
        self.container.setStyleSheet(f"""
            QWidget {{
                background-color: #1E1E1E;
                border: 1px solid {COLORS['primary']}; /* 【修改】改为主题深蓝色边框 */
                border-radius: 30px;
            }}
        """)

        # 主布局
        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(12)

        # --- 1. 左侧：超大 Logo (品牌区) ---
        self.lbl_logo = QLabel()
        self.lbl_logo.setFixedSize(42, 42)
        self.lbl_logo.setAlignment(Qt.AlignCenter)
        self.lbl_logo.setStyleSheet("border: none; background: transparent;")

        logo_path = os.path.join("assets", "logo.svg")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_logo.setPixmap(scaled_pixmap)
        else:
            self.lbl_logo.setText("⚡")
            self.lbl_logo.setStyleSheet("border:none; font-size: 28px; color: #00F3FF;")

        layout.addWidget(self.lbl_logo)

        # --- 2. 分割线 ---
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Plain)
        line.setFixedWidth(1)
        line.setFixedHeight(30)
        line.setStyleSheet("background-color: #444; border: none;")
        layout.addWidget(line)

        # --- 3. 右侧：操作区 (收藏 + 标签) ---
        # 收藏按钮
        self.btn_fav = QPushButton("☆")
        self.btn_fav.setFixedSize(32, 32)
        self.btn_fav.setToolTip("收藏")
        self.btn_fav.setCursor(Qt.PointingHandCursor)
        self.btn_fav.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: #BBB;
                border: 1px solid transparent;
                border-radius: 16px;
                font-size: 20px;
                padding-bottom: 2px;
            }}
            QPushButton:hover {{
                color: {COLORS['warning']};
                background-color: rgba(255, 255, 255, 0.05);
            }}
        """)
        self.btn_fav.clicked.connect(self._on_fav_clicked)
        layout.addWidget(self.btn_fav)

        # 常用标签栏
        self.common_tags_bar = CommonTags()
        self.common_tags_bar.tag_toggled.connect(self._on_tag_toggled)
        self.common_tags_bar.manager_requested.connect(self._on_manager_clicked)
        self.common_tags_bar.refresh_requested.connect(self._adjust_size_dynamically)

        layout.addWidget(self.common_tags_bar)

        # 阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.container.setGraphicsEffect(shadow)

    def _adjust_size_dynamically(self):
        if self.isVisible():
            self.container.adjustSize()
            self.resize(self.container.size() + QSize(30, 30))

    def show_at_mouse(self, idea_id):
        self.current_idea_id = idea_id
        self.is_favorited = False

        self.common_tags_bar.reload_tags()
        self.common_tags_bar.reset_selection()

        # 重置收藏按钮
        self.btn_fav.setText("☆")
        self.btn_fav.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: #BBB; border: 1px solid transparent; border-radius: 16px; font-size: 20px;
            }}
            QPushButton:hover {{ color: {COLORS['warning']}; background-color: rgba(255, 255, 255, 0.05); }}
        """)

        self.container.adjustSize()
        self.resize(self.container.size() + QSize(30, 30))

        cursor_pos = QCursor.pos()

        # 智能定位
        screen_geo = QApplication.desktop().screenGeometry(cursor_pos)
        win_size = self.size()

        x = cursor_pos.x() - 40
        y = cursor_pos.y() - 80

        # 边界检测
        if x + win_size.width() > screen_geo.right():
            x = screen_geo.right() - win_size.width()
        if y + win_size.height() > screen_geo.bottom():
            y = screen_geo.bottom() - win_size.height()
        if x < screen_geo.left():
            x = screen_geo.left()
        if y < screen_geo.top():
            y = screen_geo.top()

        self.move(x, y)
        self.show()

        self.hide_timer.start(3500)

    def _on_fav_clicked(self):
        if self.current_idea_id:
            if not self.is_favorited:
                self.request_favorite.emit(self.current_idea_id)
                self.is_favorited = True
                self.btn_fav.setText("★")
                self.btn_fav.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent; color: {COLORS['warning']}; border: 1px solid transparent; border-radius: 16px; font-size: 20px;
                    }}
                """)

                if self.underMouse():
                    self.hide_timer.stop()
                else:
                    self.hide_timer.start(1500)

    def _on_tag_toggled(self, tag_name, checked):
        if self.current_idea_id:
            self.request_tag_toggle.emit(self.current_idea_id, tag_name, checked)

            if self.underMouse():
                self.hide_timer.stop()
            else:
                self.hide_timer.start(1500)

    def _on_manager_clicked(self):
        self.request_manager.emit()
        self.hide()

    def _animate_hide(self):
        self.hide()

    def enterEvent(self, event):
        self.hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hide_timer.start(1000)
        super().leaveEvent(event)
