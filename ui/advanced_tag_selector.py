# -*- coding: utf-8 -*-
# ui/advanced_tag_selector.py

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLineEdit, QScrollArea, QLabel, QLayout, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QRect, QSize
from PyQt5.QtGui import QCursor, QColor
from core.config import COLORS

# --- 辅助类：流式布局 (保持云朵排列，但排序逻辑会变) ---
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super(FlowLayout, self).__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margin = self.contentsMargins()
        size += QSize(margin.left() + margin.right(), margin.top() + margin.bottom())
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0
        spacing = self.spacing()

        for item in self.itemList:
            wid = item.widget()
            spaceX = spacing + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            spaceY = spacing + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)
            
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()

# --- 主类 ---
class AdvancedTagSelector(QWidget):
    """一个功能更强大的悬浮标签选择面板 (按时间排序 + 动态图标)"""
    tags_confirmed = pyqtSignal(list)

    def __init__(self, db, idea_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.idea_id = idea_id
        
        self.selected_tags = set()
        self.tag_buttons = {} # name -> button widget
        self._is_closing = False 

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._init_ui()
        self._load_tags()
        
        # 连接全局焦点变化信号
        QApplication.instance().focusChanged.connect(self._on_focus_changed)

    def _init_ui(self):
        """初始化UI界面"""
        # 主容器
        container = QWidget()
        container.setObjectName("mainContainer")
        # 背景色调整为更深的灰，接近截图风格
        container.setStyleSheet(f"""
            #mainContainer {{
                background-color: #1E1E1E; 
                border: 1px solid #333;
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

        # 1. 搜索框 (仿截图风格)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索或新建...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: #2D2D2D; 
                border: none;
                border-bottom: 1px solid #444;
                border-radius: 4px; 
                padding: 8px; 
                font-size: 13px; 
                color: #DDD;
            }}
            QLineEdit:focus {{ border-bottom: 1px solid {COLORS['primary']}; }}
        """)
        self.search_input.textChanged.connect(self._filter_tags)
        self.search_input.returnPressed.connect(self._on_search_return)
        layout.addWidget(self.search_input)

        # 2. 标题 "最近使用"
        self.recent_label = QLabel("最近使用")
        self.recent_label.setStyleSheet("color: #888; font-size: 12px; font-weight: bold; margin-top: 5px;")
        layout.addWidget(self.recent_label)

        # 3. 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QWidget { background: transparent; }
            QScrollBar:vertical {
                border: none; background: #2D2D2D; width: 6px; margin: 0;
            }
            QScrollBar::handle:vertical { background: #555; border-radius: 3px; }
        """)
        
        self.scroll_content = QWidget()
        # 使用流式布局，标签会自动排布
        self.flow_layout = FlowLayout(self.scroll_content, margin=0, spacing=8)
        
        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll)
        
        self.setFixedSize(360, 450)

    def _load_tags(self):
        """
        从数据库加载并显示标签
        【核心修改】按最后使用时间倒序排列 (MAX(i.updated_at) DESC)
        """
        self.selected_tags = set(self.db.get_tags(self.idea_id))
        
        c = self.db.conn.cursor()
        # 这里的 SQL 逻辑是：
        # 1. 关联 ideas 表
        # 2. 取出每个标签对应的 idea 中最新的更新时间 (MAX(i.updated_at))
        # 3. 按这个时间倒序，保证最近用的排最上面
        c.execute('''
            SELECT t.name, COUNT(it.idea_id) as cnt, MAX(i.updated_at) as last_used
            FROM tags t
            LEFT JOIN idea_tags it ON t.id = it.tag_id
            LEFT JOIN ideas i ON it.idea_id = i.id AND i.is_deleted = 0
            GROUP BY t.id 
            ORDER BY last_used DESC, cnt DESC, t.name ASC
        ''')
        all_tags = c.fetchall()
        
        # 更新标题显示数量
        self.recent_label.setText(f"最近使用 ({len(all_tags)})")

        # 清空布局
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.tag_buttons.clear()

        # 生成胶囊按钮
        for row in all_tags:
            name = row[0]
            count = row[1]
            self._create_tag_chip(name, count)

    def _create_tag_chip(self, name, count=0):
        """创建一个圆角胶囊风格的标签按钮"""
        btn = QPushButton()
        btn.setCheckable(True)
        btn.setChecked(name in self.selected_tags)
        btn.setCursor(Qt.PointingHandCursor)
        
        # 将名称和数量存入属性，方便后续刷新文本
        btn.setProperty("tag_name", name)
        btn.setProperty("tag_count", count)
        
        # 初始化文本和样式
        self._update_chip_state(btn)
        
        btn.toggled.connect(lambda checked, b=btn, n=name: self._on_tag_toggled(b, n, checked))
        
        self.flow_layout.addWidget(btn)
        self.tag_buttons[name] = btn

    def _update_chip_state(self, btn):
        """根据选中状态更新：图标 + 文本 + 样式"""
        name = btn.property("tag_name")
        count = btn.property("tag_count")
        checked = btn.isChecked()
        
        # 【核心逻辑】图标切换
        # 未选中 -> 时钟图标 (🕒)
        # 选中 -> 对勾图标 (✓)
        icon = "✓" if checked else "🕒"
        text = f"{icon} {name}"
        if count > 0:
            text += f" ({count})"
        
        btn.setText(text)
        
        # 【样式逻辑】圆角胶囊 (border-radius)
        if checked:
            # 选中态：高亮色背景，白色文字
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['primary']};
                    color: white;
                    border: 1px solid {COLORS['primary']};
                    border-radius: 14px; /* 圆角 */
                    padding: 6px 12px;
                    font-size: 12px;
                    font-family: "Segoe UI", "Microsoft YaHei";
                }}
            """)
        else:
            # 未选中态：深灰背景，浅灰文字，更有质感
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2D2D2D;
                    color: #BBB;
                    border: 1px solid #444;
                    border-radius: 14px; /* 圆角 */
                    padding: 6px 12px;
                    font-size: 12px;
                    font-family: "Segoe UI", "Microsoft YaHei";
                }
                QPushButton:hover {
                    background-color: #383838;
                    border-color: #666;
                    color: white;
                }
            """)

    def _on_tag_toggled(self, button, name, checked):
        if checked:
            self.selected_tags.add(name)
        else:
            self.selected_tags.discard(name)
        # 重新渲染按钮外观（更新图标和颜色）
        self._update_chip_state(button)

    def _filter_tags(self):
        """根据搜索框内容过滤标签"""
        term = self.search_input.text().lower().strip()
        for name, btn in self.tag_buttons.items():
            if term in name.lower():
                btn.show()
            else:
                btn.hide()

    def _on_search_return(self):
        """智能回车处理"""
        text = self.search_input.text().strip()
        if not text:
            self._handle_close()
            return

        # 1. 检查是否存在完全匹配
        found_existing = False
        for name, btn in self.tag_buttons.items():
            if name.lower() == text.lower():
                if not btn.isChecked():
                    btn.setChecked(True)
                found_existing = True
                break
        
        # 2. 不存在则创建
        if not found_existing:
            self.selected_tags.add(text)
            self._create_tag_chip(text, 0)
            new_btn = self.tag_buttons.get(text)
            if new_btn: 
                new_btn.setChecked(True)
        
        self.search_input.clear()
        self._filter_tags()

    def _save_tags(self):
        """保存标签到数据库"""
        c = self.db.conn.cursor()
        c.execute('DELETE FROM idea_tags WHERE idea_id = ?', (self.idea_id,))
        for tag_name in self.selected_tags:
            c.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag_name,))
            c.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
            result = c.fetchone()
            if result:
                tag_id = result[0]
                c.execute('INSERT INTO idea_tags (idea_id, tag_id) VALUES (?, ?)', (self.idea_id, tag_id))
        self.db.conn.commit()

    def _is_child_widget(self, widget):
        if widget is None: return False
        current = widget
        while current:
            if current is self: return True
            current = current.parent()
        return False

    def _on_focus_changed(self, old_widget, new_widget):
        if self._is_closing or not self.isVisible(): return
        if not self._is_child_widget(new_widget):
            self._handle_close()

    def _handle_close(self):
        if self._is_closing: return
        self._is_closing = True
        try:
            QApplication.instance().focusChanged.disconnect(self._on_focus_changed)
        except: pass
        self._save_tags()
        self.tags_confirmed.emit(list(self.selected_tags))
        self.close()

    def show_at_cursor(self):
        cursor_pos = QCursor.pos()
        screen_geo = QApplication.desktop().screenGeometry()
        x, y = cursor_pos.x() + 15, cursor_pos.y() + 15
        if x + self.width() > screen_geo.right(): x = cursor_pos.x() - self.width() - 15
        if y + self.height() > screen_geo.bottom(): y = screen_geo.bottom() - self.height() - 15
        self.move(x, y)
        self.show()
        self.activateWindow()
        self.search_input.setFocus()