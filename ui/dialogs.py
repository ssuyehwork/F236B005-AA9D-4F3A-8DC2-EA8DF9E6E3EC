# ui/dialogs.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QHBoxLayout,
                              QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton,
                              QProgressBar, QFrame, QApplication, QMessageBox, QShortcut,
                             QSpacerItem, QSizePolicy, QSplitter, QWidget, QScrollBar)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt, QTimer
from core.config import STYLES, COLORS

# ... (SCROLLBAR_STYLE and BaseDialog remain the same) ...
SCROLLBAR_STYLE = """
QScrollBar:vertical {
    border: none; background: #222222; width: 10px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #555555; min-height: 20px; border-radius: 5px;
}
QScrollBar::handle:vertical:hover { background: #666666; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal {
    border: none; background: #222222; height: 10px; margin: 0;
}
QScrollBar::handle:horizontal {
    background: #555555; min-width: 20px; border-radius: 5px;
}
QScrollBar::handle:horizontal:hover { background: #666666; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
"""

class BaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLES['dialog'] + SCROLLBAR_STYLE)

class EditDialog(BaseDialog):
    def __init__(self, db, idea_id=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.idea_id = idea_id
        self.selected_color = COLORS['primary']
        self.category_id = None
        self.is_new_idea = (idea_id is None) # 判断是新建还是编辑

        self._init_ui()
        if not self.is_new_idea:
            self._load_data()

        self._setup_auto_save()

    def _init_ui(self):
        self.setWindowTitle('✨ 记录灵感')
        self.resize(950, 650)

        main_layout = QVBoxLayout(self)
        # ... (rest of the UI setup is identical) ...
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{ background-color: {COLORS['bg_mid']}; width: 2px; margin: 0 5px; }}
            QSplitter::handle:hover {{ background-color: {COLORS['primary']}; }}
        """)
        left_container = QWidget()
        left_panel = QVBoxLayout(left_container)
        left_panel.setContentsMargins(15, 15, 15, 15)
        left_panel.setSpacing(12)
        left_panel.addWidget(QLabel('📌 标题'))
        self.title_inp = QLineEdit()
        self.title_inp.setPlaceholderText("请输入灵感标题...")
        self.title_inp.setFixedHeight(40)
        left_panel.addWidget(self.title_inp)
        left_panel.addWidget(QLabel('🏷️ 标签'))
        self.tags_inp = QLineEdit()
        self.tags_inp.setPlaceholderText("使用逗号分隔...")
        self.tags_inp.setFixedHeight(40)
        left_panel.addWidget(self.tags_inp)
        left_panel.addSpacing(10)
        left_panel.addWidget(QLabel('🎨 标记颜色'))
        color_layout = QGridLayout()
        color_layout.setSpacing(10)
        self.color_btns = []
        colors = [COLORS['primary'], COLORS['success'], COLORS['warning'], COLORS['danger'], COLORS['info'], COLORS['teal']]
        for i, c in enumerate(colors):
            btn = QPushButton()
            btn.setFixedSize(34, 34)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"QPushButton {{ background-color: {c}; border-radius: 17px; border: 2px solid transparent; }}")
            btn.clicked.connect(lambda _, x=c: self._set_color(x))
            self.color_btns.append(btn)
            color_layout.addWidget(btn, i // 3, i % 3)
        left_panel.addLayout(color_layout)
        left_panel.addStretch()
        self.save_btn = QPushButton('💾 保存 (Ctrl+S)')
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setFixedHeight(50)
        self.save_btn.setStyleSheet(STYLES['btn_primary'])
        self.save_btn.clicked.connect(self.save_and_close) # 修改连接
        left_panel.addWidget(self.save_btn)
        right_container = QWidget()
        right_panel = QVBoxLayout(right_container)
        right_panel.setContentsMargins(15, 15, 15, 15)
        right_panel.setSpacing(10)
        right_panel.addWidget(QLabel('📝 详细内容'))
        self.content_inp = QTextEdit()
        self.content_inp.setPlaceholderText("在这里记录详细内容...")
        self.content_inp.setStyleSheet("QTextEdit { background-color: #2a2a2a; border: 1px solid #444; border-radius: 8px; padding: 10px; font-size: 14px; color: #eee; }")
        right_panel.addWidget(self.content_inp)
        self.splitter.addWidget(left_container)
        self.splitter.addWidget(right_container)
        self.splitter.setSizes([300, 650])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        main_layout.addWidget(self.splitter)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_and_close) # 修改连接
        self._set_color(self.selected_color)

    def _setup_auto_save(self):
        """配置并启动自动保存定时器"""
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setInterval(7000) # 7秒
        self.auto_save_timer.timeout.connect(self._auto_save)
        self.auto_save_timer.start()

    def _set_color(self, color):
        # ... (identical) ...
        self.selected_color = color
        for btn in self.color_btns:
            style = btn.styleSheet()
            if color in style:
                new_style = f"background-color: {color}; border-radius: 17px; border: 3px solid white;"
            else:
                bg = style.split('background-color:')[1].split(';')[0].strip()
                new_style = f"background-color: {bg}; border-radius: 17px; border: 2px solid transparent;"
            btn.setStyleSheet(f"QPushButton {{ {new_style} }}")

    def _load_data(self):
        # ... (identical) ...
        d = self.db.get_idea(self.idea_id)
        if d:
            self.title_inp.setText(d[1])
            self.content_inp.setText(d[2])
            self._set_color(d[3])
            self.category_id = d[8]
            self.tags_inp.setText(','.join(self.db.get_tags(self.idea_id)))

    def _perform_save(self):
        """执行核心的保存逻辑，不关闭窗口"""
        title = self.title_inp.text().strip()
        if not title:
            # 对于自动保存，如果标题为空，则静默失败，不打扰用户
            if not self.is_new_idea:
                print("[DEBUG] Auto-save skipped: title is empty.")
            return False

        tags = [t.strip() for t in self.tags_inp.text().split(',') if t.strip()]
        args = (title, self.content_inp.toPlainText(), self.selected_color, tags, self.category_id)

        if self.idea_id:
            self.db.update_idea(self.idea_id, *args)
        else:
            # 如果是新建的笔记，第一次保存后就获取ID，后续自动保存变为更新操作
            self.idea_id = self.db.add_idea(*args)
            self.is_new_idea = False # 状态变为编辑

        print(f"[DEBUG] Data saved for idea_id: {self.idea_id}")
        return True

    def _auto_save(self):
        """自动保存的槽函数"""
        print("[DEBUG] Auto-saving...")
        self._perform_save()

    def save_and_close(self):
        """手动保存并关闭窗口"""
        title = self.title_inp.text().strip()
        if not title:
            self.title_inp.setPlaceholderText("⚠️ 标题不能为空！")
            self.title_inp.setFocus()
            return

        if self._perform_save():
            self.accept() # 保存成功后才关闭

    def closeEvent(self, event):
        """重写关闭事件以停止定时器"""
        self.auto_save_timer.stop()
        print("[DEBUG] EditDialog closed, auto-save timer stopped.")
        super().closeEvent(event)

    def reject(self):
        """处理 Escape 键或窗口关闭按钮"""
        self.auto_save_timer.stop()
        print("[DEBUG] EditDialog rejected, auto-save timer stopped.")
        super().reject()

# ... (StatsDialog and ExtractDialog remain the same) ...
class StatsDialog(BaseDialog):
    # ...
    pass
class ExtractDialog(BaseDialog):
    # ...
    pass
