# -*- coding: utf-8 -*-
# ui/components/search_line_edit.py

from PyQt5.QtWidgets import (QLineEdit, QListWidget, QListWidgetItem, QPushButton,
                               QHBoxLayout, QWidget, QDialog, QVBoxLayout, QLabel)
from PyQt5.QtCore import Qt, QSettings, QPoint
from PyQt5.QtGui import QColor, QPalette


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
        if not text:
            return

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
        return self.settings.value(self.SETTINGS_KEY, [], type=list)

    def remove_history_entry(self, text):
        """
        从历史记录中删除一个词条。
        """
        history = self.get_history()
        if text in history:
            history.remove(text)
            self.settings.setValue(self.SETTINGS_KEY, history)

    def show_history_popup(self):
        """
        显示包含搜索历史的下拉弹窗。
        """
        history = self.get_history()
        if not history:
            return

        self.history_popup = QDialog(self, Qt.Popup)
        self.history_popup.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        # 设置窗口背景透明
        self.history_popup.setAttribute(Qt.WA_TranslucentBackground, True)

        list_widget = QListWidget(self.history_popup)
        # 为QListWidget设置样式，使其看起来像一个浮动面板
        list_widget.setStyleSheet("""
            QListWidget {
                background-color: #2E2E32;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 5px;
                color: #E0E0E0;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #3A3A3E;
            }
            QListWidget::item:selected {
                background-color: #007ACC;
                color: white;
            }
        """)

        for item_text in history:
            list_item = QListWidgetItem(list_widget)
            item_widget = self.create_history_item_widget(item_text, list_widget)
            list_item.setSizeHint(item_widget.sizeHint())
            list_widget.addItem(list_item)
            list_widget.setItemWidget(list_item, item_widget)

        list_widget.itemClicked.connect(self.on_history_item_clicked)

        layout = QHBoxLayout(self.history_popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(list_widget)

        # 定位弹窗
        pos = self.mapToGlobal(QPoint(0, self.height()))
        self.history_popup.move(pos)
        self.history_popup.setFixedWidth(self.width())
        self.history_popup.adjustSize()
        self.history_popup.show()

    def create_history_item_widget(self, text, parent):
        """
        为历史记录列表的每一项创建一个自定义控件（包含文本和删除按钮）。
        """
        widget = QWidget(parent)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 0, 5, 0)
        layout.setSpacing(10)

        label = QLabel(text)
        label.setStyleSheet("border: none; background: transparent; color: #E0E0E0;")

        del_button = QPushButton("✕")
        del_button.setFixedSize(20, 20)
        del_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #666;
                border-radius: 10px;
                color: #999;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #E81123;
                border-color: #E81123;
                color: white;
            }
        """)
        del_button.setCursor(Qt.PointingHandCursor)
        del_button.clicked.connect(lambda: self.on_delete_history_item(text))

        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(del_button)

        return widget

    def on_history_item_clicked(self, item):
        """
        当历史记录项被点击时，设置搜索框文本并关闭弹窗。
        """
        # 从自定义控件中获取文本
        widget = self.history_popup.findChild(QListWidget).itemWidget(item)
        if widget:
            text = widget.findChild(QLabel).text()
            self.setText(text)
            self.history_popup.close()
            self.returnPressed.emit() # 模拟回车，触发搜索

    def on_delete_history_item(self, text):
        """
        删除指定的历史记录项，并刷新弹窗。
        """
        self.remove_history_entry(text)
        # 关闭旧的弹窗并重新打开以刷新内容
        if self.history_popup:
            self.history_popup.close()
        self.show_history_popup()

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    
    # 设置一个深色主题方便预览
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(45, 45, 50))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(30, 30, 35))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 60))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 60))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)

    main_window = QWidget()
    main_window.setWindowTitle("SearchLineEdit Test")
    main_window.setGeometry(300, 300, 400, 200)

    layout = QVBoxLayout(main_window)
    
    search_box = SearchLineEdit()
    search_box.setPlaceholderText("双击此处查看历史记录...")
    search_box.setStyleSheet("""
        QLineEdit {
            border: 1px solid #555;
            border-radius: 15px;
            padding: 5px 15px;
            background-color: #2E2E32;
            color: #E0E0E0;
            font-size: 14px;
        }
    """)
    
    # 添加一些虚拟的历史记录用于测试
    search_box.add_history_entry("PyQt5 tutorial")
    search_box.add_history_entry("QSettings example")
    search_box.add_history_entry("Custom QLineEdit")

    def on_search():
        term = search_box.text()
        print(f"正在搜索: {term}")
        search_box.add_history_entry(term)

    search_box.returnPressed.connect(on_search)
    
    layout.addWidget(search_box)
    layout.addStretch()

    main_window.show()
    
    sys.exit(app.exec_())