# -*- coding: utf-8 -*-
import sys
import ctypes
from ctypes import wintypes
import time
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QListWidget, QLineEdit, 
                             QListWidgetItem, QHBoxLayout, QTreeWidget, QTreeWidgetItem, 
                             QPushButton, QStyle, QAction, QSplitter, QGraphicsDropShadowEffect, QLabel, QTreeWidgetItemIterator, QShortcut)
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, QSettings, QUrl, QMimeData, pyqtSignal, QObject
from PyQt5.QtGui import QImage, QColor, QCursor, QPixmap, QPainter, QIcon, QKeySequence

from services.idea_service import IdeaService
from services.clipboard_service import ClipboardService
from core.enums import FilterType

# =================================================================================
#   Win32 API (To be refactored into a platform service later)
# =================================================================================
if sys.platform == "win32":
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    KEYEVENTF_KEYUP = 0x0002
    VK_CONTROL = 0x11
    VK_V = 0x56
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOACTIVATE = 0x0010
    SWP_FLAGS = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
    class GUITHREADINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD), ("hwndActive", wintypes.HWND), ("hwndFocus", wintypes.HWND), ("hwndCapture", wintypes.HWND), ("hwndMenuOwner", wintypes.HWND), ("hwndMoveSize", wintypes.HWND), ("hwndCaret", wintypes.HWND), ("rcCaret", wintypes.RECT)]
else:
    user32 = None
    kernel32 = None

# =================================================================================
#   STYLESHEET
# =================================================================================
DARK_STYLESHEET = """
QWidget#Container { background-color: #1e1e1e; border: 1px solid #333333; border-radius: 8px; }
QWidget { color: #cccccc; font-family: "Microsoft YaHei", "Segoe UI Emoji"; font-size: 14px; }
QLabel#TitleLabel { color: #858585; font-weight: bold; font-size: 15px; padding-left: 5px; }
QListWidget, QTreeWidget { border: none; background-color: #1e1e1e; alternate-background-color: #252526; outline: none; }
QListWidget::item { padding: 8px; border: none; }
QListWidget::item:selected, QTreeWidget::item:selected { background-color: #4a90e2; color: #FFFFFF; }
QListWidget::item:hover { background-color: #444444; }
QSplitter::handle { background-color: #333333; width: 2px; }
QSplitter::handle:hover { background-color: #4a90e2; }
QLineEdit { background-color: #252526; border: 1px solid #333333; border-radius: 4px; padding: 6px; font-size: 16px; }
QPushButton#ToolButton, QPushButton#MinButton, QPushButton#CloseButton, QPushButton#PinButton, QPushButton#MaxButton { background-color: transparent; border-radius: 4px; padding: 0px; font-size: 16px; font-weight: bold; text-align: center; }
QPushButton#ToolButton:hover, QPushButton#MinButton:hover, QPushButton#MaxButton:hover { background-color: #444; }
QPushButton#ToolButton:checked, QPushButton#MaxButton:checked { background-color: #555; border: 1px solid #666; }
QPushButton#CloseButton:hover { background-color: #E81123; color: white; }
QPushButton#PinButton:hover { background-color: #444; }
QPushButton#PinButton:checked { background-color: #0078D4; color: white; border: 1px solid #005A9E; }
"""

class QuickWindow(QWidget):
    RESIZE_MARGIN = 18 
    open_main_window_requested = pyqtSignal()

    def __init__(self, idea_service: IdeaService, clipboard_service: ClipboardService):
        super().__init__()
        self.idea_service = idea_service
        self.clipboard_service = clipboard_service
        self.settings = QSettings("MyTools", "RapidNotes")
        
        self.m_drag = False
        self.m_DragPosition = QPoint()
        self.resize_area = None
        self._is_pinned = False
        self.last_active_hwnd = None
        self.my_hwnd = None
        self._processing_clipboard = False

        self.clipboard = QApplication.clipboard()
        
        self._init_ui()
        self._connect_signals()
        self._restore_window_state()
        
        self.setMouseTracking(True)
        
        if user32:
            self.monitor_timer = QTimer(self)
            self.monitor_timer.timeout.connect(self._monitor_foreground_window)
            self.monitor_timer.start(200)

        self._update_partition_tree()
        self._update_list()

    def _init_ui(self):
        self.setWindowTitle("快速笔记")
        self.resize(830, 630)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(15, 15, 15, 15) 
        
        self.container = QWidget(self)
        self.container.setObjectName("Container")
        self.container.setMouseTracking(True)
        self.root_layout.addWidget(self.container)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.container.setGraphicsEffect(shadow)
        
        self.setStyleSheet(DARK_STYLESHEET)
        
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        self._create_title_bar()
        self._create_search_bar()
        self._create_main_content()
        self._create_status_bar()

    def _create_title_bar(self):
        title_bar_layout = QHBoxLayout()
        title_bar_layout.setContentsMargins(0, 0, 0, 0)
        title_bar_layout.setSpacing(5)
        
        self.title_label = QLabel("⚡️ 快速笔记")
        self.title_label.setObjectName("TitleLabel")
        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch()
        
        self.btn_stay_top = QPushButton("📌", self)
        self.btn_stay_top.setObjectName("PinButton")
        self.btn_stay_top.setToolTip("保持置顶")
        self.btn_stay_top.setCheckable(True)
        self.btn_stay_top.setFixedSize(32, 32)

        self.btn_toggle_side = QPushButton("👁️", self)
        self.btn_toggle_side.setObjectName("ToolButton")
        self.btn_toggle_side.setToolTip("显示/隐藏侧边栏")
        self.btn_toggle_side.setFixedSize(32, 32)
        
        self.btn_open_full = QPushButton(self)
        self.btn_open_full.setObjectName("MaxButton")
        self.btn_open_full.setToolTip("打开主程序界面")
        self.btn_open_full.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        self.btn_open_full.setFixedSize(32, 32)

        self.btn_minimize = QPushButton("—", self)
        self.btn_minimize.setObjectName("MinButton")
        self.btn_minimize.setToolTip("最小化")
        self.btn_minimize.setFixedSize(32, 32)
        
        self.btn_close = QPushButton(self)
        self.btn_close.setObjectName("CloseButton")
        self.btn_close.setToolTip("关闭")
        self.btn_close.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        self.btn_close.setFixedSize(32, 32)
        
        title_bar_layout.addWidget(self.btn_stay_top)
        title_bar_layout.addWidget(self.btn_toggle_side)
        title_bar_layout.addWidget(self.btn_open_full)
        title_bar_layout.addWidget(self.btn_minimize)
        title_bar_layout.addWidget(self.btn_close)
        
        self.main_layout.addLayout(title_bar_layout)

    def _create_search_bar(self):
        self.search_box = QLineEdit(self)
        self.search_box.setPlaceholderText("搜索或新增笔记...")
        self.clear_action = QAction(self)
        self.clear_action.setIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton))
        self.search_box.addAction(self.clear_action, QLineEdit.TrailingPosition)
        self.main_layout.addWidget(self.search_box)

    def _create_main_content(self):
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(4)
        
        self.list_widget = QListWidget()
        self.list_widget.setFocusPolicy(Qt.StrongFocus)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.partition_tree = QTreeWidget()
        self.partition_tree.setHeaderHidden(True)
        self.partition_tree.setFocusPolicy(Qt.NoFocus)
        self.partition_tree.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.partition_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.splitter.addWidget(self.list_widget)
        self.splitter.addWidget(self.partition_tree)
        self.splitter.setSizes([550, 150])
        
        content_layout.addWidget(self.splitter)
        self.main_layout.addWidget(content_widget, 1)

    def _create_status_bar(self):
        self.partition_status_label = QLabel("当前分区: 全部数据")
        self.partition_status_label.setObjectName("PartitionStatusLabel")
        self.partition_status_label.setStyleSheet("font-size: 11px; color: #888; padding-left: 5px;")
        self.main_layout.addWidget(self.partition_status_label)
        self.partition_status_label.hide()

    def _connect_signals(self):
        self.clipboard.dataChanged.connect(self.on_clipboard_changed)
        self.clipboard_service.data_captured.connect(self._update_list)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._update_list)

        self.search_box.textChanged.connect(self._on_search_text_changed)
        self.list_widget.itemActivated.connect(self._on_item_activated)
        self.partition_tree.currentItemChanged.connect(self._on_partition_selection_changed)

        self.clear_action.triggered.connect(self.search_box.clear)
        self.search_box.textChanged.connect(lambda text: self.clear_action.setVisible(bool(text)))
        self.clear_action.setVisible(False)

        self.btn_stay_top.clicked.connect(self._toggle_stay_on_top)
        self.btn_toggle_side.clicked.connect(self._toggle_partition_panel)
        self.btn_open_full.clicked.connect(self.open_main_window_requested)
        self.btn_minimize.clicked.connect(self.showMinimized)
        self.btn_close.clicked.connect(self.close)

        self.partition_tree.currentItemChanged.connect(self._update_partition_status_display)
        QShortcut(QKeySequence("Ctrl+W"), self, self.close)

    def _restore_window_state(self):
        if geometry := self.settings.value("geometry"):
            self.restoreGeometry(geometry)
        if splitter_state := self.settings.value("splitter_state"):
            self.splitter.restoreState(splitter_state)

        is_hidden = self.settings.value("partition_panel_hidden", False, type=bool)
        self.partition_tree.setHidden(is_hidden)
        self._update_partition_status_display()

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("splitter_state", self.splitter.saveState())
        self.hide()
        event.ignore()

    def _get_resize_area(self, pos):
        m = self.RESIZE_MARGIN
        w, h = self.width(), self.height()
        areas = []
        if pos.x() < m: areas.append('left')
        elif pos.x() > w - m: areas.append('right')
        if pos.y() < m: areas.append('top')
        elif pos.y() > h - m: areas.append('bottom')
        return areas

    def _set_cursor_for_resize(self, areas):
        if not areas:
            self.setCursor(Qt.ArrowCursor)
        elif ('left' in areas and 'top' in areas) or ('right' in areas and 'bottom' in areas):
            self.setCursor(Qt.SizeFDiagCursor)
        elif ('left' in areas and 'bottom' in areas) or ('right' in areas and 'top' in areas):
            self.setCursor(Qt.SizeBDiagCursor)
        elif 'left' in areas or 'right' in areas:
            self.setCursor(Qt.SizeHorCursor)
        else: # top or bottom
            self.setCursor(Qt.SizeVerCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.resize_area = self._get_resize_area(event.pos())
            if self.resize_area:
                self.m_drag = False
            else:
                self.m_drag = True
                self.m_DragPosition = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.NoButton:
            areas = self._get_resize_area(event.pos())
            self._set_cursor_for_resize(areas)
            return

        if self.resize_area:
            rect = self.geometry()
            gpos = event.globalPos()
            if 'left' in self.resize_area: rect.setLeft(gpos.x())
            if 'right' in self.resize_area: rect.setWidth(gpos.x() - rect.left())
            if 'top' in self.resize_area: rect.setTop(gpos.y())
            if 'bottom' in self.resize_area: rect.setHeight(gpos.y() - rect.top())
            self.setGeometry(rect)
        elif self.m_drag:
            self.move(event.globalPos() - self.m_DragPosition)

    def mouseReleaseEvent(self, event):
        self.m_drag = False
        self.resize_area = None
        self.setCursor(Qt.ArrowCursor)

    def showEvent(self, event):
        if not self.my_hwnd and user32:
            self.my_hwnd = int(self.winId())
        super().showEvent(event)

    def _monitor_foreground_window(self):
        if user32:
            hwnd = user32.GetForegroundWindow()
            if hwnd != 0 and hwnd != self.my_hwnd:
                self.last_active_hwnd = hwnd

    def _on_search_text_changed(self):
        self.search_timer.start(300)

    def _update_list(self):
        search_text = self.search_box.text()
        f_type, f_val = FilterType.ALL.value, None

        if current_partition := self.partition_tree.currentItem():
            if data := current_partition.data(0, Qt.UserRole):
                f_type = data.get('type', FilterType.ALL.value)
                if f_type == FilterType.CATEGORY.value:
                    f_val = data.get('id')

        items = self.idea_service.get_ideas_for_filter(search_text, f_type, f_val)
        self.list_widget.clear()
        
        for item_tuple in items:
            display_text = str(item_tuple[1] or item_tuple[2] or "").replace('\n', ' ').strip()[:150]
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, item_tuple)
            if item_tuple[2]:
                list_item.setToolTip(str(item_tuple[2])[:500])
            self.list_widget.addItem(list_item)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _create_color_icon(self, color_str):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(color_str or "#808080"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(2, 2, 12, 12, 4, 4)
        painter.end()
        return QIcon(pixmap)

    def _update_partition_tree(self):
        counts = self.idea_service.get_stats_counts()
        partition_counts = counts.get('categories', {})
        self.partition_tree.clear()
        
        static_items = [
            ("全部数据", {'type': FilterType.ALL.value}, QStyle.SP_DirHomeIcon, counts.get(FilterType.ALL.value, 0)),
            ("今日数据", {'type': FilterType.TODAY.value}, QStyle.SP_FileDialogDetailedView, counts.get(FilterType.TODAY.value, 0))
        ]
        for name, data, icon, count in static_items:
            item = QTreeWidgetItem(self.partition_tree, [f"{name} ({count})"])
            item.setData(0, Qt.UserRole, data)
            item.setIcon(0, self.style().standardIcon(icon))
        
        top_level_partitions = self.idea_service.get_category_tree()
        self._add_partition_recursive(top_level_partitions, self.partition_tree, partition_counts)

        self.partition_tree.expandAll()
        if self.partition_tree.topLevelItemCount() > 0:
            self.partition_tree.setCurrentItem(self.partition_tree.topLevelItem(0))

    def _add_partition_recursive(self, partitions, parent_item, partition_counts):
        for p in partitions:
            count = partition_counts.get(p.id, 0)
            item = QTreeWidgetItem(parent_item, [f"{p.name} ({count})"])
            item.setData(0, Qt.UserRole, {'type': FilterType.CATEGORY.value, 'id': p.id, 'color': p.color})
            item.setIcon(0, self._create_color_icon(p.color))
            if p.children:
                self._add_partition_recursive(p.children, item, partition_counts)

    def _update_partition_status_display(self):
        if self.partition_tree.isHidden():
            if current := self.partition_tree.currentItem():
                self.partition_status_label.setText(f"当前: {current.text(0).split(' (')[0]}")
            self.partition_status_label.show()
        else:
            self.partition_status_label.hide()

    def _on_partition_selection_changed(self, current, previous):
        self._update_list()
        self._update_partition_status_display()
        
    def _toggle_partition_panel(self):
        is_hidden = not self.partition_tree.isVisible()
        self.partition_tree.setHidden(is_hidden)
        self.settings.setValue("partition_panel_hidden", is_hidden)
        self._update_partition_status_display()
    
    def _toggle_stay_on_top(self):
        if not user32: return
        self._is_pinned = self.btn_stay_top.isChecked()
        hwnd = int(self.winId())
        flag = HWND_TOPMOST if self._is_pinned else HWND_NOTOPMOST
        user32.SetWindowPos(hwnd, flag, 0, 0, 0, 0, SWP_FLAGS)

    def _on_item_activated(self, item):
        item_tuple = item.data(Qt.UserRole)
        if not item_tuple: return
        try:
            clipboard = QApplication.clipboard()
            item_type = item_tuple[10] if len(item_tuple) > 10 else 'text'
            
            if item_type == 'image' and item_tuple[11]:
                clipboard.setImage(QImage.fromData(item_tuple[11]))
            elif item_type == 'file' and item_tuple[2]:
                mime_data = QMimeData()
                urls = [QUrl.fromLocalFile(p) for p in item_tuple[2].split(';') if p]
                mime_data.setUrls(urls)
                clipboard.setMimeData(mime_data)
            else:
                clipboard.setText(item_tuple[2] or "")
            self._paste_ditto_style()
        except Exception as e:
            print(f"❌ 粘贴操作失败: {e}")

    def _paste_ditto_style(self):
        if not user32 or not self.last_active_hwnd or not user32.IsWindow(self.last_active_hwnd):
            return

        user32.SetForegroundWindow(self.last_active_hwnd)
        time.sleep(0.05) # Small delay to ensure window is focused

        # Simulate Ctrl+V
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_V, 0, 0, 0)
        user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

    def on_clipboard_changed(self):
        if self._processing_clipboard:
            return
        self._processing_clipboard = True
        try:
            self.clipboard_service.process_mime_data(self.clipboard.mimeData())
        finally:
            self._processing_clipboard = False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() in (Qt.Key_Up, Qt.Key_Down) and not self.list_widget.hasFocus():
            self.list_widget.setFocus()
            QApplication.sendEvent(self.list_widget, event)
        else:
            super().keyPressEvent(event)
