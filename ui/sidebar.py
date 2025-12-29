# -*- coding: utf-8 -*-
# ui/sidebar.py
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox, QInputDialog, QFrame, QApplication
from PyQt5.QtCore import Qt, pyqtSignal, QSize

from core.config import COLORS
from core.logger import get_logger

logger = get_logger(__name__)

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
        logger.debug("侧边栏初始化完成")

    def refresh(self):
        logger.debug("开始刷新侧边栏...")
        self.clear()
        try:
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
            item_map = {}

            # First pass: add top-level categories (groups)
            for cat in categories:
                if cat[2] is None:
                    count = counts.get('categories', {}).get(cat[0], 0)
                    item = QTreeWidgetItem(user_group, [f"📂 {cat[1]} ({count})"])
                    item.setData(0, Qt.UserRole, ('category', cat[0]))
                    item.setFlags(item.flags() | Qt.ItemIsDropEnabled)
                    item_map[cat[0]] = item

            # Second pass: add child categories (areas)
            for cat in categories:
                if cat[2] is not None:
                    parent_item = item_map.get(cat[2])
                    if parent_item:
                        count = counts.get('categories', {}).get(cat[0], 0)
                        item = QTreeWidgetItem(parent_item, [f"📄 {cat[1]} ({count})"])
                        item.setData(0, Qt.UserRole, ('category', cat[0]))
                        item_map[cat[0]] = item
            logger.info(f"侧边栏刷新成功, 加载了 {len(categories)} 个分类")
        except Exception as e:
            logger.error(f"刷新侧边栏时发生错误: {e}", exc_info=True)

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
                if not target_item:
                    logger.warning("外部拖放目标项无效")
                    return

                target_data = target_item.data(0, Qt.UserRole)
                if not target_data: return

                type, val = target_data
                logger.info(f"外部拖放: 笔记 {iid} -> 目标类型={type}, 值={val}")

                if type == 'category': self.db.move_category(iid, val)
                elif type == 'system' and val == 'uncategorized': self.db.move_category(iid, None)
                elif type == 'system' and val == 'trash': self.db.set_deleted(iid, True)
                elif type == 'system' and val == 'favorite': self.db.toggle_field(iid, 'is_favorite')

                self.data_changed.emit()
                self.refresh()
                e.accept()
            except Exception as err:
                logger.error(f"处理外部拖放时出错: {err}", exc_info=True)
            return

        # --- Case 2: 内部条目拖拽排序 ---
        logger.debug("内部拖放事件开始")
        super().dropEvent(e) # 调用父类的默认实现来处理InternalMove

        # 在默认实现处理完移动后，我们更新数据库
        self.update_order_from_tree()
        self.data_changed.emit()
        logger.info("内部拖放完成，分类结构已更新")

    def update_order_from_tree(self):
        """遍历tree，更新所有用户分类的parent_id和sort_order"""
        try:
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
            logger.debug("数据库中的分类结构已根据UI更新")
        except IndexError:
            logger.error("无法找到'我的分类'根项，无法更新顺序")
        except Exception as e:
            logger.error(f"更新分类结构时出错: {e}", exc_info=True)

    def _on_click(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data:
            f_type, val = data
            logger.debug(f"侧边栏项被点击: 原始类型={f_type}, 值={val}")

            # 关键修复：对于系统视图，我们直接使用它的值（如 'all', 'today'）作为筛选类型
            if f_type == 'system':
                # 将 f_type 从 'system' 修正为 'all', 'today' 等
                correct_f_type = val
                # val 对于系统视图通常是 None 或与 f_type 相同
                correct_val = None
                logger.info(f"修正系统视图点击事件: 类型='{correct_f_type}', 值='{correct_val}'")
                self.filter_changed.emit(correct_f_type, correct_val)
            else:
                # 对于 'category', 'root_category' 等，维持原有逻辑
                self.filter_changed.emit(f_type, val)

    def _show_menu(self, pos):
        item = self.itemAt(pos)
        if not item: return

        data = item.data(0, Qt.UserRole)
        if not data: return

        f_type, val = data
        menu = QMenu()

        if f_type == 'root_category':
            menu.addAction("➕ 新建组", lambda: self._new_category(is_group=True))
        elif f_type == 'category':
            cat = self.db.get_category(val)
            if cat:
                # 如果是组 (没有 parent_id)
                if cat[2] is None:
                    menu.addAction("➕ 新建区", lambda: self._new_category(parent_id=val))
                menu.addAction("✏️ 重命名", lambda: self._rename_category(val, cat[1]))
                menu.addAction("🗑️ 删除", lambda: self._del_category(val))
        else: # system folders
            return

        logger.debug(f"显示右键菜单: 类型={f_type}, 值={val}")
        menu.exec_(self.mapToGlobal(pos))

    def _new_category(self, is_group=False, parent_id=None):
        name, ok = QInputDialog.getText(self, '新建分类', '请输入名称:')
        if ok and name:
            self.db.add_category(name, parent_id)
            logger.info(f"新建分类: 名称='{name}', parent_id={parent_id}")
            self.refresh()
            self.data_changed.emit()

    def _rename_category(self, cat_id, old_name):
        name, ok = QInputDialog.getText(self, '重命名', '新名称:', text=old_name)
        if ok and name and name != old_name:
            self.db.rename_category(cat_id, name)
            logger.info(f"重命名分类: ID={cat_id}, 旧名称='{old_name}', 新名称='{name}'")
            self.refresh()

    def _del_category(self, cid):
        cat = self.db.get_category(cid)
        if not cat: return

        child_count = self.db.get_child_category_count(cid)
        note_count = self.db.get_notes_in_category_count(cid)

        warning_msg = f"确定要删除分类 '{cat[1]}' 吗？"
        if child_count > 0:
            warning_msg += f"\n\n警告：此操作将同时删除其下的 {child_count} 个子分类"
        if note_count > 0:
            warning_msg += f"\n\n其下的 {note_count} 条笔记将被移至'未分类'。"

        if QMessageBox.Yes == QMessageBox.warning(self, '确认删除', warning_msg, QMessageBox.Yes | QMessageBox.No):
            self.db.delete_category(cid)
            logger.warning(f"删除分类: ID={cid}, 名称='{cat[1]}'")
            self.refresh()
            self.data_changed.emit()
