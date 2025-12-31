# ui/dialogs.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QHBoxLayout,
                              QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton,
                              QProgressBar, QFrame, QApplication, QMessageBox, QShortcut,
                             QSpacerItem, QSizePolicy, QSplitter, QWidget, QScrollBar,
                             QGraphicsDropShadowEffect)
from PyQt5.QtGui import QKeySequence, QColor, QPixmap
from PyQt5.QtCore import Qt
from core.config import STYLES, COLORS
from .components.rich_text_edit import RichTextEdit
from services.idea_service import IdeaService
from core.enums import FilterType

# ... (SCROLLBAR_STYLE and BaseDialog remain the same) ...
SCROLLBAR_STYLE = """
QScrollBar:vertical {
    border: none;
    background: #222222;
    width: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #555555;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #666666;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QScrollBar:horizontal {
    border: none;
    background: #222222;
    height: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:horizontal {
    background: #555555;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #666666;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}
"""

class BaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._setup_container()
    
    def _setup_container(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(15, 15, 15, 15)
        
        self.content_container = QWidget()
        self.content_container.setObjectName("DialogContainer")
        self.content_container.setStyleSheet(f"""
            #DialogContainer {{
                background-color: {COLORS['bg_dark']};
                border-radius: 12px;
            }}
        """ + STYLES['dialog'] + SCROLLBAR_STYLE)
        
        outer_layout.addWidget(self.content_container)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.content_container.setGraphicsEffect(shadow)
        
        return self.content_container

class EditDialog(BaseDialog):
    # ... (EditDialog implementation remains the same) ...
    def __init__(self, idea_service: IdeaService, idea_id=None, parent=None, category_id_for_new=None): # Changed signature
        super().__init__(parent)
        self.idea_service = idea_service # Use service
        self.idea_id = idea_id
        self.selected_color = COLORS['primary']
        self.category_id = None
        self.category_id_for_new = category_id_for_new
        
        self._init_ui()
        if idea_id: self._load_data()
        
        self._drag_pos = None

    def _init_ui(self):
        self.setWindowTitle('✨ 记录灵感')
        self.resize(950, 650)
        
        main_layout = QVBoxLayout(self.content_container)
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
        colors = [COLORS['primary'], COLORS['success'], COLORS['warning'],
                  COLORS['danger'], COLORS['info'], COLORS['teal']]
                  
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
        self.save_btn.clicked.connect(self._save_data)
        left_panel.addWidget(self.save_btn)
        
        right_container = QWidget()
        right_panel = QVBoxLayout(right_container)
        right_panel.setContentsMargins(15, 15, 15, 15)
        right_panel.setSpacing(10)
        
        right_panel.addWidget(QLabel('📝 详细内容'))
        self.content_inp = RichTextEdit()
        self.content_inp.setPlaceholderText("在这里记录详细内容（支持粘贴图片）...")
        self.content_inp.setStyleSheet("QTextEdit { background-color: #2a2a2a; border: 1px solid #444; border-radius: 8px; padding: 10px; font-size: 14px; color: #eee; }")
        right_panel.addWidget(self.content_inp)
        
        self.splitter.addWidget(left_container)
        self.splitter.addWidget(right_container)
        self.splitter.setSizes([300, 650])
        
        main_layout.addWidget(self.splitter)
        
        QShortcut(QKeySequence("Ctrl+S"), self, self._save_data)
        QShortcut(QKeySequence("Escape"), self, self.reject)
        self._set_color(self.selected_color)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.pos().y() < 40:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(e.globalPos() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def _set_color(self, color):
        self.selected_color = color
        for btn in self.color_btns:
            is_selected = color in btn.styleSheet()
            border_style = "3px solid white" if is_selected else "2px solid transparent"
            bg_color = color if is_selected else btn.styleSheet().split('background-color:')[1].split(';')[0].strip()
            btn.setStyleSheet(f"QPushButton {{ background-color: {bg_color}; border-radius: 17px; border: {border_style}; }}")

    def _load_data(self):
        d = self.idea_service.get_idea_with_blob(self.idea_id) # Use service
        if d:
            self.title_inp.setText(d[1])
            self.content_inp.setText(d[2])
            self._set_color(d[3])
            self.category_id = d[8]
            
            item_type = d[9]
            data_blob = d[10]
            if item_type == 'image' and data_blob:
                self.content_inp.set_image_data(data_blob)

            self.tags_inp.setText(','.join(self.idea_service.get_idea_tags(self.idea_id))) # Use service

    def _save_data(self):
        title = self.title_inp.text().strip()
        if not title:
            self.title_inp.setPlaceholderText("⚠️ 标题不能为空!")
            self.title_inp.setFocus()
            return

        tags = [t.strip() for t in self.tags_inp.text().split(',') if t.strip()]
        content = self.content_inp.toPlainText()
        color = self.selected_color
        
        item_type = 'text'
        data_blob = self.content_inp.get_image_data()
        if data_blob:
            item_type = 'image'

        # Use service
        if self.idea_id:
            self.idea_service.update_idea(self.idea_id, title, content, color, tags, self.category_id, item_type, data_blob)
        else:
            self.idea_service.add_idea(title, content, color, tags, self.category_id_for_new, item_type, data_blob)
        
        self.accept()

class StatsDialog(BaseDialog):
    # ... (StatsDialog implementation remains the same) ...
    def __init__(self, idea_service: IdeaService, parent=None): # Changed signature
        super().__init__(parent)
        self.setWindowTitle('📊 数据看板')
        self.resize(550, 450)
        
        layout = QVBoxLayout(self.content_container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        counts = idea_service.get_stats_counts() # Use service
        grid = QGridLayout()
        grid.setSpacing(15)
        grid.addWidget(self._box("📚 总灵感", counts.get('all', 0), COLORS['primary']), 0, 0)
        grid.addWidget(self._box("📅 今日新增", counts.get('today', 0), COLORS['success']), 0, 1)
        grid.addWidget(self._box("⭐ 我的收藏", counts.get('favorite', 0), COLORS['warning']), 1, 0)
        grid.addWidget(self._box("🏷️ 待整理", counts.get('untagged', 0), COLORS['danger']), 1, 1)
        layout.addLayout(grid)
        
        layout.addSpacing(10)
        layout.addWidget(QLabel("🔥 热门标签 Top 5"))
        
        stats = idea_service.get_all_tags_with_counts() # Use service
        if not stats:
            layout.addWidget(QLabel("暂无标签数据", styleSheet="color:#666; font-style:italic; font-weight:normal;"))
        else:
            max_val = stats[0][1] if stats else 1
            for name, cnt in stats:
                h = QHBoxLayout()
                lbl = QLabel(f"#{name}")
                lbl.setFixedWidth(80)
                h.addWidget(lbl)
                
                p = QProgressBar()
                p.setMaximum(max_val)
                p.setValue(cnt)
                p.setFixedHeight(18)
                p.setFormat(f" {cnt}")
                p.setStyleSheet(f"QProgressBar {{ background-color: {COLORS['bg_mid']}; border: none; border-radius: 9px; color: white; text-align: center; }} QProgressBar::chunk {{ background-color: {COLORS['primary']}; border-radius: 9px; }}")
                h.addWidget(p)
                layout.addLayout(h)
                
        layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setFixedHeight(40)
        close_btn.setStyleSheet(f"background-color:{COLORS['bg_mid']}; border:1px solid #444; color:#ccc; border-radius:5px;")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _box(self, t, v, c):
        f = QFrame()
        f.setStyleSheet(f"QFrame {{ background-color: {c}15; border: 1px solid {c}40; border-radius: 10px; }}")
        vl = QVBoxLayout(f)
        lbl_title = QLabel(t)
        lbl_title.setStyleSheet(f"color:{c}; font-size:13px; font-weight:bold; border:none; margin:0;")
        lbl_val = QLabel(str(v))
        lbl_val.setStyleSheet(f"color:{c}; font-size:28px; font-weight:bold; border:none; margin-top:5px;")
        vl.addWidget(lbl_title)
        vl.addWidget(lbl_val)
        return f

class ExtractDialog(BaseDialog):
    # ... (ExtractDialog implementation remains the same) ...
    def __init__(self, idea_service: IdeaService, parent=None): # Changed signature
        super().__init__(parent)
        self.setWindowTitle('📋 提取内容')
        self.resize(700, 600)
        
        layout = QVBoxLayout(self.content_container)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setPlaceholderText("暂无数据...")
        layout.addWidget(self.txt)
        
        data = idea_service.get_ideas_for_filter('', FilterType.ALL.value, None) # Use service
        lines = ['='*60, '💡 灵感闪记 - 内容导出', '='*60, '']
        for d in data:
            lines.append(f"【{d[1]}】")
            if d[2]: lines.append(f"\n{d[2]}")
            lines.append('\n'+'-'*60+'\n')

        text = '\n'.join(lines)
        self.txt.setText(text)
        
        layout.addSpacing(10)
        btn = QPushButton('📋 复制全部到剪贴板')
        btn.setFixedHeight(45)
        btn.setStyleSheet(STYLES['btn_primary'])
        btn.clicked.connect(lambda: (QApplication.clipboard().setText(text), QMessageBox.information(self,'成功','✅ 内容已复制')))
        layout.addWidget(btn)

