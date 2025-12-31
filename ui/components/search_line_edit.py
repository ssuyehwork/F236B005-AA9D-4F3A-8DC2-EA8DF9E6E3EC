# -*- coding: utf-8 -*-
# ui/components/search_line_edit.py
from PyQt5.QtWidgets import (QLineEdit, QPushButton, QHBoxLayout, QWidget, QDialog, 
                             QVBoxLayout, QApplication, QLabel, QLayout, QScrollArea)
from PyQt5.QtCore import Qt, QSettings, QPoint, QRect, QSize
from PyQt5.QtGui import QColor, QPalette, QFont


class FlowLayout(QLayout):
    """
    流式布局，支持自动换行的弹性排列。
    """
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.item_list.append(item)

    def count(self):
        return len(self.item_list)

    def itemAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())
        margin = self.contentsMargins()
        size += QSize(margin.left() + margin.right(), margin.top() + margin.bottom())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self.item_list:
            widget = item.widget()
            space_x = spacing
            space_y = spacing

            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()


class SearchLineEdit(QLineEdit):
    """
    一个带有搜索历史记录功能的 QLineEdit。
    """
    MAX_HISTORY_COUNT = 20
    SETTINGS_KEY = "SearchHistory"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.history_popup = None
        self.settings = QSettings("KMain_V3", "KMain_V3")
        
        # 确保字体设置正确
        font = QFont()
        font.setFamily("Microsoft YaHei UI")  # 使用微软雅黑
        font.setPointSize(10)
        self.setFont(font)

    def mouseDoubleClickEvent(self, event):
        """
        双击时显示历史记录弹窗。
        """
        self.show_history_popup()
        super().mouseDoubleClickEvent(event)

    def add_history_entry(self, text):
        """
        将新的搜索词添加到历史记录中。
        """
        if not text or not text.strip():
            return
            
        text = text.strip()
        history = self.get_history()
        
        if text in history:
            history.remove(text)
        history.insert(0, text)

        # 保持历史记录不超过最大数量
        while len(history) > self.MAX_HISTORY_COUNT:
            history.pop()
            
        self.settings.setValue(self.SETTINGS_KEY, history)

    def get_history(self):
        """
        从 QSettings 中获取历史记录。
        """
        history = self.settings.value(self.SETTINGS_KEY, [], type=list)
        # 过滤空值
        return [h for h in history if h and h.strip()]

    def remove_history_entry(self, text):
        """
        从历史记录中删除一个词条。
        """
        history = self.get_history()
        if text in history:
            history.remove(text)
            self.settings.setValue(self.SETTINGS_KEY, history)

    def clear_history(self):
        """
        清空所有历史记录。
        """
        self.settings.setValue(self.SETTINGS_KEY, [])

    def show_history_popup(self):
        """
        显示包含搜索历史的下拉弹窗（流式双列布局）。
        """
        history = self.get_history()
        if not history:
            return

        # 如果弹窗已存在，先关闭
        if self.history_popup:
            self.history_popup.close()

        self.history_popup = QDialog(self, Qt.Popup | Qt.FramelessWindowHint)
        self.history_popup.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # 主容器
        main_widget = QWidget()
        main_widget.setStyleSheet("""
            QWidget {
                background-color: #2E2E32;
                border: 1px solid #444;
                border-radius: 8px;
            }
        """)
        
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

        # 创建流式布局容器
        from PyQt5.QtWidgets import QScrollArea
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2E2E32;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #555;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666;
            }
        """)
        
        content_widget = QWidget()
        content_layout = FlowLayout(content_widget)
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 设置字体
        font = QFont()
        font.setFamily("Microsoft YaHei UI")
        font.setPointSize(9)

        # 添加历史记录项
        for item_text in history:
            item_button = self.create_flow_history_item(item_text, font)
            content_layout.addWidget(item_button)

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # 将主容器添加到对话框
        dialog_layout = QVBoxLayout(self.history_popup)
        dialog_layout.setContentsMargins(5, 5, 5, 5)
        dialog_layout.addWidget(main_widget)

        # 定位弹窗（考虑高DPI）
        pos = self.mapToGlobal(QPoint(0, self.height() + 2))
        self.history_popup.move(pos)
        
        # 设置宽度和最大高度
        popup_width = max(self.width() * 2, 400)  # 增加宽度以适应双列
        self.history_popup.setFixedWidth(popup_width)
        
        # 设置最大高度
        max_height = 250
        scroll_area.setMaximumHeight(max_height)
        
        self.history_popup.adjustSize()
        self.history_popup.show()

    def create_flow_history_item(self, text, font):
        """
        为流式布局创建历史记录项（带删除按钮的标签式按钮）。
        """
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # 文本按钮
        text_btn = QPushButton(text)
        text_btn.setFont(font)
        text_btn.setCursor(Qt.PointingHandCursor)
        text_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3E;
                border: 1px solid #555;
                border-radius: 15px;
                color: #E0E0E0;
                padding: 6px 12px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #007ACC;
                border-color: #007ACC;
                color: white;
            }
        """)
        text_btn.clicked.connect(lambda: self.on_flow_item_clicked(text))

        # 删除按钮
        del_button = QPushButton("×")
        del_button.setFixedSize(24, 24)
        del_button.setFont(font)
        del_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #666;
                border-radius: 12px;
                color: #999;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E81123;
                border-color: #E81123;
                color: white;
            }
        """)
        del_button.setCursor(Qt.PointingHandCursor)
        del_button.clicked.connect(lambda: self.on_delete_flow_item(text))

        layout.addWidget(text_btn)
        layout.addWidget(del_button)

        return container

    def on_flow_item_clicked(self, text):
        """
        流式布局项被点击时的处理。
        """
        self.setText(text)
        if self.history_popup:
            self.history_popup.close()
        self.returnPressed.emit()

    def on_delete_flow_item(self, text):
        """
        删除流式布局中的历史记录项。
        """
        self.remove_history_entry(text)
        if self.history_popup:
            self.history_popup.close()
            self.show_history_popup()


