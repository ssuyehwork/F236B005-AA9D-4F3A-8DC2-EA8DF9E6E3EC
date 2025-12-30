# -*- coding: utf-8 -*-
# ui/sidebar.py
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox, QInputDialog, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor
from core.config import COLORS

class Sidebar(QTreeWidget):
    filter_changed = pyqtSignal(str, object)
    data_changed = pyqtSignal()
    new_idea_in_category = pyqtSignal(int)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setHeaderHidden(True)
        self.setIndentation(15)
        self.setAcceptDrops(True)

        # 优化样式：极简紧凑布局
        self.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {COLORS['bg_mid']};
                color: #ddd;
                border: none;
                font-size: 13px;
                padding: 2px;
                outline: none;
            }}
            QTreeWidget::item {{
                height: 24px;
                padding: 1px 4px;
                border-radius: 4px;
                margin-bottom: 0px;
            }}
            QTreeWidget::item:hover {{
                background-color: #2a2d2e;
            }}
            QTreeWidget::item:selected {{
                background-color: #37373d;
                color: white;
            }}
        """)

        self.itemClicked.connect(self._on_click)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self.refresh()

    def refresh(self):
        self.clear()
        counts = self.db.get_counts()

        # 1. 系统内置分类
        menu_items = [
            ("全部数据", 'all', '🗂️'), ("今日数据", 'today', '📅'),
            ("未分类", 'uncategorized', '⚠️'), ("未标签", 'untagged', '🏷️'),
            ("收藏", 'favorite', '⭐'), ("回收站", 'trash', '🗑️')
        ]

        for name, key, icon in menu_items:
            item = QTreeWidgetItem(self, [f"{icon}  {name} ({counts.get(key, 0)})"])
            item.setData(0, Qt.UserRole, (key, None))
        
        # --- 分割线 ---
        sep_item = QTreeWidgetItem(self)
        sep_item.setFlags(Qt.NoItemFlags) # 不可选中/点击
        sep_item.setSizeHint(0, QSize(0, 12))

        line_frame = QFrame()
        line_frame.setFixedHeight(1)
        line_frame.setStyleSheet(f"background-color: {COLORS['bg_light']}; margin: 0px 8px;")
        self.setItemWidget(sep_item, 0, line_frame)

        # 2. 动态分类（组/区）
        partitions_tree = self.db.get_partitions_tree()
        self._add_partition_items(partitions_tree, self, counts.get('categories', {}))
        self.expandAll()

    def _add_partition_items(self, partitions, parent_item, counts):
        for part in partitions:
            count = counts.get(part.id, 0)

            display_text = f"{part.name} ({count})"

            # 组或区都创建为 QTreeWidgetItem
            item = QTreeWidgetItem(parent_item, [display_text])

            if part.parent_id is None: # 这是一个“组”
                 font = item.font(0)
                 font.setBold(True)
                 item.setFont(0, font)
                 # 组本身不可交互，仅作为分类头
                 item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            else: # 这是一个“区”
                item.setText(0, f"📂 {display_text}")
                item.setData(0, Qt.UserRole, ('category', part.id))

            # 递归添加子项
            if part.children:
                self._add_partition_items(part.children, item, counts)


    # --- 其余逻辑保持不变 ---
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat('application/x-idea-id'): e.accept()
        else: e.ignore()

    def dragMoveEvent(self, e):
        item = self.itemAt(e.pos())
        if item:
            d = item.data(0, Qt.UserRole)
            if d and d[0] in ['category', 'trash', 'favorite', 'uncategorized']:
                self.setCurrentItem(item)
                e.accept()
                return
        e.ignore()

    def dropEvent(self, e):
        try:
            iid = int(e.mimeData().data('application/x-idea-id'))
            item = self.itemAt(e.pos())
            if not item: return
            d = item.data(0, Qt.UserRole)
            if not d: return
            key, val = d
            if key == 'category': self.db.move_category(iid, val)
            elif key == 'uncategorized': self.db.move_category(iid, None)
            elif key == 'trash': self.db.set_deleted(iid, True)
            elif key == 'favorite': self.db.set_favorite(iid, True)
            self.data_changed.emit()
            self.refresh()
        except Exception as err:
            print(f"Drop error: {err}")

    def _on_click(self, item):
        data = item.data(0, Qt.UserRole)
        if data: self.filter_changed.emit(*data)

    def _show_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("background:#2d2d2d;color:white")
        menu.addAction('➕ 新建文件夹', self._new_category)
        item = self.itemAt(pos)
        if item and item.data(0, Qt.UserRole) and item.data(0, Qt.UserRole)[0] == 'category':
            cat_id = item.data(0, Qt.UserRole)[1]
            raw_text = item.text(0)
            current_name = raw_text.split(' (')[0].replace('📂 ', '')
            menu.addAction('➕ 新建数据', lambda: self.new_idea_in_category.emit(cat_id))
            menu.addSeparator()
            menu.addAction('✏️ 重命名', lambda: self._rename_category(cat_id, current_name))
            menu.addAction('🗑️ 删除文件夹', lambda: self._del_category(cat_id))
        menu.exec_(self.mapToGlobal(pos))

    def _new_category(self):
        text, ok = QInputDialog.getText(self, '新建', '名称:')
        if ok and text:
            self.db.add_category(text)
            self.refresh()

    def _rename_category(self, cat_id, old_name):
        text, ok = QInputDialog.getText(self, '重命名', '新名称:', text=old_name)
        if ok and text and text.strip():
            self.db.rename_category(cat_id, text.strip())
            self.refresh()

    def _del_category(self, cid):
        if QMessageBox.yes == QMessageBox.question(self, '确认', '删除此文件夹? (内容移至未分类)'):
            self.db.delete_category(cid)
            self.refresh()
