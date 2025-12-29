# -*- coding: utf-8 -*-
# ui/advanced_tag_selector.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLineEdit, QScrollArea, QLabel, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QCursor, QFont
from core.config import COLORS

class AdvancedTagSelector(QWidget):
    """一个功能更强大的悬浮标签选择面板"""
    tags_confirmed = pyqtSignal(list)

    def __init__(self, db, idea_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.idea_id = idea_id

        # --- 状态变量 ---
        self.selected_tags = set()
        self.tag_widgets = {} # { "tagName": {"button": QPushButton, "group": QWidget} }

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)

        self._init_ui()
        self._load_tags()

    def _init_ui(self):
        """初始化UI界面"""
        container = QWidget()
        container.setObjectName("mainContainer")
        container.setStyleSheet(f"""
            #mainContainer {{
                background-color: #282828;
                border: 1px solid #444;
                border-radius: 8px;
                color: #EEE;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索标签...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: #3C3C3C; border: 1px solid #555;
                border-radius: 6px; padding: 7px 10px; font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {COLORS['primary']}; }}
        """)
        self.search_input.textChanged.connect(self._filter_tags)
        layout.addWidget(self.search_input)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                border: none; background: #3C3C3C; width: 8px;
                margin: 0; border-radius: 4px;
            }
            QScrollBar::handle:vertical { background: #555; min-height: 25px; border-radius: 4px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 5, 0, 5)
        self.scroll_layout.setSpacing(12)
        self.scroll_layout.setAlignment(Qt.AlignTop)

        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll)

        self.setFixedSize(320, 480)

    def _load_tags(self):
        """从数据库加载并显示标签"""
        # 1. 获取当前笔记已有的标签
        self.selected_tags = set(self.db.get_tags(self.idea_id))

        # 2. 获取所有标签及其使用频率
        c = self.db.conn.cursor()
        c.execute('''
            SELECT t.name, COUNT(it.idea_id) as cnt
            FROM tags t
            LEFT JOIN idea_tags it ON t.id = it.tag_id
            JOIN ideas i ON it.idea_id = i.id AND i.is_deleted = 0
            GROUP BY t.id ORDER BY cnt DESC, t.name ASC
        ''')
        all_tags = c.fetchall()

        # 3. 定义分组逻辑
        #    - 最常用的前12个为“最近/常用”
        #    - 其余为“其它”
        top_tags = all_tags[:12]
        other_tags = all_tags[12:]

        # 4. 创建UI
        if top_tags:
            self._create_group("最近使用", top_tags)
        if other_tags:
            self._create_group("其它", other_tags)

        self._filter_tags() # 初始过滤一次，以防搜索框有内容

    def _create_group(self, title, tags):
        """创建标签分组的UI"""
        group_container = QWidget()
        group_layout = QVBoxLayout(group_container)
        group_layout.setContentsMargins(0,0,0,0)
        group_layout.setSpacing(8)

        group_label = QLabel(f"{title} ({len(tags)})")
        group_label.setStyleSheet("color: #AAA; font-size: 12px; margin-top: 5px; margin-bottom: 2px;")
        group_layout.addWidget(group_label)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0,0,0,0)
        grid.setSpacing(8)

        row, col = 0, 0
        for name, count in tags:
            btn = QPushButton(f"{name} ({count})")
            btn.setCheckable(True)
            btn.setChecked(name in self.selected_tags)
            btn.setStyleSheet(self._get_button_style(btn.isChecked()))
            btn.toggled.connect(lambda checked, b=btn, n=name: self._on_tag_toggled(b, n, checked))

            grid.addWidget(btn, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

            self.tag_widgets[name] = {"button": btn, "group": group_container, "group_label": group_label}

        group_layout.addWidget(grid_widget)
        self.scroll_layout.addWidget(group_container)

    def _on_tag_toggled(self, button, name, checked):
        """处理标签按钮的点击事件"""
        button.setStyleSheet(self._get_button_style(checked))
        if checked:
            self.selected_tags.add(name)
            # 在按钮文本前添加勾号
            if not button.text().startswith("✓"):
                button.setText(f"✓ {button.text()}")
        else:
            self.selected_tags.discard(name)
            # 移除文本前的勾号
            button.setText(button.text().replace("✓ ", ""))

    def _filter_tags(self):
        """根据搜索框内容过滤标签"""
        term = self.search_input.text().lower()

        visible_tags_in_group = {}

        for name, widgets in self.tag_widgets.items():
            button = widgets["button"]
            group_label = widgets["group_label"]

            # 初始化分组计数
            if group_label not in visible_tags_in_group:
                visible_tags_in_group[group_label] = 0

            if term in name.lower():
                button.show()
                visible_tags_in_group[group_label] += 1
            else:
                button.hide()

        # 根据分组内的可见标签数，决定是否显示分组容器
        for name, widgets in self.tag_widgets.items():
             group_container = widgets["group"]
             group_label = widgets["group_label"]
             if visible_tags_in_group.get(group_label, 0) > 0:
                 group_container.show()
             else:
                 group_container.hide()

    def _get_button_style(self, checked):
        """根据选中状态返回按钮样式"""
        # 移除文本前的勾号，以正确设置样式
        base_style = """
            QPushButton {{
                border-radius: 6px; padding: 7px; text-align: left;
                font-size: 13px; border: 1px solid {border_color};
                background-color: {bg_color}; color: {text_color};
            }}
            QPushButton:hover {{
                background-color: #4A4A4A; border-color: #666;
            }}
        """
        if checked:
            return base_style.format(
                bg_color=COLORS['primary'],
                border_color=COLORS['primary'],
                text_color='white'
            )
        else:
            return base_style.format(
                bg_color="#3C3C3C",
                border_color="#555",
                text_color="#DDD"
            )

    def _save_tags(self):
        """将最终选择的标签保存到数据库"""
        print(f"[DEBUG] 正在为 idea_id={self.idea_id} 保存标签: {self.selected_tags}")
        c = self.db.conn.cursor()
        # 1. 清空此笔记的所有旧标签关联
        c.execute('DELETE FROM idea_tags WHERE idea_id = ?', (self.idea_id,))

        # 2. 重新插入所有选中的标签关联
        for tag_name in self.selected_tags:
            # 确保标签存在于 tags 表中 (通常情况下一定存在)
            c.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag_name,))
            c.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
            result = c.fetchone()
            if result:
                tag_id = result[0]
                c.execute('INSERT INTO idea_tags (idea_id, tag_id) VALUES (?, ?)',
                          (self.idea_id, tag_id))
        self.db.conn.commit()
        print(f"[DEBUG] 标签保存成功。")

    def show_at_cursor(self):
        cursor_pos = QCursor.pos()
        screen_geo = self.screen().geometry()
        x, y = cursor_pos.x() + 15, cursor_pos.y() + 15
        if x + self.width() > screen_geo.right(): x = cursor_pos.x() - self.width() - 15
        if y + self.height() > screen_geo.bottom(): y = screen_geo.bottom() - self.height() - 15
        self.move(x, y)
        self.show()
        self.activateWindow()
        self.search_input.setFocus()

    def focusOutEvent(self, event):
        self._save_tags()
        self.tags_confirmed.emit(list(self.selected_tags))
        self.close()
        super().focusOutEvent(event)
