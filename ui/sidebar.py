# -*- coding: utf-8 -*-
# ui/sidebar.py
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox, QInputDialog, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor
from core.config import COLORS
from services.idea_service import IdeaService
from core.enums import FilterType # New dependency

class Sidebar(QTreeWidget):
    filter_changed = pyqtSignal(str, object)
    data_changed = pyqtSignal()
    new_data_requested = pyqtSignal(int)

    def __init__(self, idea_service: IdeaService, parent=None):
        super().__init__(parent)
        self.idea_service = idea_service
        self.setHeaderHidden(True)
        self.setIndentation(15)
        
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(self.InternalMove)

        self.setStyleSheet(f"""
            QTreeWidget {{ background-color: {COLORS['bg_mid']}; color: #ddd; border: none; font-size: 13px; padding: 2px; outline: none; }}
            QTreeWidget::item {{ height: 24px; padding: 1px 4px; border-radius: 4px; margin-bottom: 0px; }}
            QTreeWidget::item:hover {{ background-color: #2a2d2e; }}
            QTreeWidget::item:selected {{ background-color: #37373d; color: white; }}
        """)

        self.itemClicked.connect(self._on_click)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self.refresh()

    def refresh(self):
        self.clear()
        self.setColumnCount(1)
        counts = self.idea_service.get_stats_counts()

        system_menu_items = [
            ("全部数据", FilterType.ALL, '🗂️'), ("今日数据", FilterType.TODAY, '📅'),
            ("剪贴板数据", FilterType.CLIPBOARD, '📋'),
            ("未分类", FilterType.UNCATEGORIZED, '⚠️'), ("未标签", FilterType.UNTAGGED, '🏷️'),
            ("收藏", FilterType.FAVORITE, '⭐'), ("回收站", FilterType.TRASH, '🗑️')
        ]

        for name, key_enum, icon in system_menu_items:
            item = QTreeWidgetItem(self, [f"{icon}  {name} ({counts.get(key_enum.value, 0)})"])
            item.setData(0, Qt.UserRole, (key_enum.value, None))
            item.setFlags(item.flags() & ~Qt.ItemIsDragEnabled)
            item.setExpanded(False)

        sep_item = QTreeWidgetItem(self); sep_item.setFlags(Qt.NoItemFlags); sep_item.setSizeHint(0, QSize(0, 15))
        line_frame = QFrame(); line_frame.setFixedHeight(1); line_frame.setStyleSheet(f"background-color: {COLORS['bg_light']}; margin: 0px 8px;")
        self.setItemWidget(sep_item, 0, line_frame)

        user_partitions_root = QTreeWidgetItem(self, ["🗃️ 我的分区"])
        user_partitions_root.setFlags(user_partitions_root.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsDragEnabled)
        font = user_partitions_root.font(0); font.setBold(True); user_partitions_root.setFont(0, font); user_partitions_root.setForeground(0, QColor("#FFFFFF"))
        
        partitions_tree = self.idea_service.get_category_tree()
        self._add_partition_recursive(partitions_tree, user_partitions_root, counts.get('categories', {}))
        
        self.expandAll()

    def _add_partition_recursive(self, partitions, parent_item, counts):
        for p in partitions:
            count = counts.get(p.id, 0) + sum(counts.get(child.id, 0) for child in p.children)
            icon = "📦" if not p.children else "🗃️"
            item = QTreeWidgetItem(parent_item, [f"{icon} {p.name} ({count})"])
            item.setData(0, Qt.UserRole, (FilterType.CATEGORY.value, p.id))
            if p.children:
                self._add_partition_recursive(p.children, item, counts)

    def dragMoveEvent(self, e):
        item = self.itemAt(e.pos())
        if item and (d := item.data(0, Qt.UserRole)):
            allowed_keys = [FilterType.CATEGORY.value, FilterType.TRASH.value, FilterType.FAVORITE.value, FilterType.UNCATEGORIZED.value]
            if d[0] in allowed_keys:
                self.setCurrentItem(item); e.accept(); return
        super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasFormat('application/x-idea-id'):
            try:
                iid = int(e.mimeData().data('application/x-idea-id'))
                item = self.itemAt(e.pos())
                if item and (d := item.data(0, Qt.UserRole)):
                    key, val = d
                    if key == FilterType.CATEGORY.value: self.idea_service.move_to_category([iid], val)
                    elif key == FilterType.UNCATEGORIZED.value: self.idea_service.move_to_category([iid], None)
                    elif key == FilterType.TRASH.value: self.idea_service.move_to_trash([iid])
                    elif key == FilterType.FAVORITE.value: self.idea_service.toggle_favorite(iid)
                    self.data_changed.emit(); self.refresh()
                    e.acceptProposedAction()
            except Exception as err:
                print(f"Drop error: {err}")
        else:
            super().dropEvent(e)
            self._save_current_order()

    def _save_current_order(self):
        update_list = []
        def iterate_items(parent_item, parent_id):
            for i in range(parent_item.childCount()):
                item = parent_item.child(i)
                if (data := item.data(0, Qt.UserRole)) and data[0] == FilterType.CATEGORY.value:
                    cat_id = data[1]
                    update_list.append({'id': cat_id, 'sort_order': i, 'parent_id': parent_id})
                    if item.childCount() > 0: iterate_items(item, cat_id)

        # Find the root item for user partitions to start iteration
        root_items = self.findItems("🗃️ 我的分区", Qt.MatchExactly)
        if root_items: iterate_items(root_items[0], None)
        
        if update_list: self.idea_service.save_category_order(update_list)

    def _on_click(self, item):
        if data := item.data(0, Qt.UserRole): self.filter_changed.emit(*data)

    def _show_menu(self, pos):
        item = self.itemAt(pos)
        menu = QMenu(self); menu.setStyleSheet("background:#2d2d2d;color:white")

        if not item or item.text(0) == "🗃️ 我的分区":
            menu.addAction('➕ 组', self._new_group).exec_(self.mapToGlobal(pos))
            return

        if (data := item.data(0, Qt.UserRole)) and data[0] == FilterType.CATEGORY.value:
            cat_id = data[1]; current_name = ' '.join(item.text(0).split(' ')[:-1]).strip()[2:]
            menu.addAction('➕ 数据', lambda: self.new_data_requested.emit(cat_id))
            menu.addSeparator()
            menu.addAction('➕ 组', self._new_group)
            menu.addAction('➕ 区', lambda: self._new_zone(cat_id))
            menu.addAction('✏️ 重命名', lambda: self._rename_category(cat_id, current_name))
            menu.addAction('🗑️ 删除', lambda: self._del_category(cat_id))
            menu.exec_(self.mapToGlobal(pos))

    def _new_group(self):
        text, ok = QInputDialog.getText(self, '新建组', '组名称:')
        if ok and text:
            self.idea_service.add_category(text, parent_id=None)
            self.refresh()
            
    def _new_zone(self, parent_id):
        text, ok = QInputDialog.getText(self, '新建区', '区名称:')
        if ok and text:
            self.idea_service.add_category(text, parent_id=parent_id)
            self.refresh()

    def _rename_category(self, cat_id, old_name):
        text, ok = QInputDialog.getText(self, '重命名', '新名称:', text=old_name)
        if ok and text.strip():
            self.idea_service.rename_category(cat_id, text.strip())
            self.refresh()

    def _del_category(self, cid):
        # A more robust implementation would get child info from the service
        msg = '确认删除此分类? (其中的内容将移至未分类)'
        if QMessageBox.Yes == QMessageBox.question(self, '确认删除', msg):
            self.idea_service.delete_category(cid)
            self.refresh()
