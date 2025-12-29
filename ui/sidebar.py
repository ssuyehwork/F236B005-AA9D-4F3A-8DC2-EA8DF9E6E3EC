# -*- coding: utf-8 -*-
# ui/sidebar.py
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox, QInputDialog, QFrame, QApplication
from PyQt5.QtCore import Qt, pyqtSignal, QSize

from core.config import COLORS

class Sidebar(QTreeWidget):
    filter_changed = pyqtSignal(str, object)
    data_changed = pyqtSignal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db

        self.setHeaderHidden(True)
        self.setIndentation(15)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(self.InternalMove) # Default mode

        self.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {COLORS['bg_mid']};
                color: #ddd; border: none; font-size: 13px; padding: 2px; outline: none;
            }}
            QTreeWidget::item {{ height: 28px; padding: 1px 4px; border-radius: 4px; }}
            QTreeWidget::item:hover {{ background-color: #2a2d2e; }}
            QTreeWidget::item:selected {{ background-color: #37373d; color: white; }}
            QTreeWidget::branch {{ image: none; }}
        """)

        self.itemClicked.connect(self._on_click)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)

        self.refresh()

    def refresh(self):
        # ... (identical to previous version) ...
        self.clear()
        counts = self.db.get_counts()
        system_group = QTreeWidgetItem(self, ["系统视图"])
        system_group.setFlags(system_group.flags() & ~Qt.ItemIsDropEnabled)
        system_group.setExpanded(True)
        menu_items = [
            ("全部数据", 'all', '🗂️'), ("今日数据", 'today', '📅'),
            ("未分类", 'uncategorized', '⚠️'), ("收藏", 'favorite', '⭐'),
            ("回收站", 'trash', '🗑️')
        ]
        for name, key, icon in menu_items:
            item = QTreeWidgetItem(system_group, [f"{icon}  {name} ({counts.get(key, 0)})"])
            item.setData(0, Qt.UserRole, ('system', key))
            item.setFlags(item.flags() & ~Qt.ItemIsDragEnabled)
        user_group = QTreeWidgetItem(self, ["我的分类"])
        user_group.setFlags(user_group.flags() | Qt.ItemIsDropEnabled)
        user_group.setData(0, Qt.UserRole, ('root_category', None))
        user_group.setExpanded(True)
        categories = self.db.get_categories()
        cat_map = {c[0]: c for c in categories}
        item_map = {}
        for cat in categories:
            if cat[2] is None:
                count = counts['categories'].get(cat[0], 0)
                item = QTreeWidgetItem(user_group, [f"📂 {cat[1]} ({count})"])
                item.setData(0, Qt.UserRole, ('category', cat[0]))
                item.setFlags(item.flags() | Qt.ItemIsDropEnabled)
                item_map[cat[0]] = item
        for cat in categories:
            if cat[2] is not None:
                parent_item = item_map.get(cat[2])
                if parent_item:
                    count = counts['categories'].get(cat[0], 0)
                    item = QTreeWidgetItem(parent_item, [f"📄 {cat[1]} ({count})"])
                    item.setData(0, Qt.UserRole, ('category', cat[0]))
                    item_map[cat[0]] = item

    def dragEnterEvent(self, e):
        # 同时接受内部拖拽和外部的笔记卡片拖拽
        if e.mimeData().hasFormat('application/x-qabstractitemmodeldatalist') or \
           e.mimeData().hasFormat('application/x-idea-id'):
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        mime_data = e.mimeData()

        # --- Case 1: 外部笔记卡片拖入 ---
        if mime_data.hasFormat('application/x-idea-id'):
            try:
                iid = int(mime_data.data('application/x-idea-id'))
                target_item = self.itemAt(e.pos())
                if not target_item: return

                target_data = target_item.data(0, Qt.UserRole)
                if not target_data: return

                type, val = target_data

                if type == 'category': self.db.move_category(iid, val)
                elif type == 'system' and val == 'uncategorized': self.db.move_category(iid, None)
                elif type == 'system' and val == 'trash': self.db.set_deleted(iid, True)
                elif type == 'system' and val == 'favorite': self.db.toggle_field(iid, 'is_favorite')

                self.data_changed.emit()
                self.refresh()
                e.accept()
            except Exception as err:
                print(f"Error handling external drop: {err}")
            return

        # --- Case 2: 内部条目拖拽排序 ---
        # 调用父类的默认实现来处理InternalMove
        super().dropEvent(e)

        # 在默认实现处理完移动后，我们更新数据库
        self.update_order_from_tree()
        self.data_changed.emit()

    def update_order_from_tree(self):
        """遍历tree，更新所有用户分类的parent_id和sort_order"""
        root_category_item = self.findItems("我的分类", Qt.MatchExactly)[0]

        # 遍历所有“组”
        for i in range(root_category_item.childCount()):
            group_item = root_category_item.child(i)
            group_id = group_item.data(0, Qt.UserRole)[1]
            self.db.update_category_structure(group_id, None, i)

            # 遍历该组下的所有“区”
            for j in range(group_item.childCount()):
                area_item = group_item.child(j)
                area_id = area_item.data(0, Qt.UserRole)[1]
                self.db.update_category_structure(area_id, group_id, j)

    def _on_click(self, item):
        # ... (identical) ...
        pass

    def _show_menu(self, pos):
        # ... (identical) ...
        pass

    def _new_category(self, is_group=False, parent_id=None):
        # ... (identical) ...
        pass

    def _rename_category(self, cat_id, old_name):
        # ... (identical) ...
        pass

    def _del_category(self, cid):
        # ... (identical) ...
        pass
