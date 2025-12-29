# -*- coding: utf-8 -*-
# ui/ball.py
import math
from PyQt5.QtWidgets import QWidget, QMenu
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt5.QtGui import QPainter, QRadialGradient, QColor, QFont
from core.settings import save_setting

class FloatingBall(QWidget):
    double_clicked = pyqtSignal()

    def __init__(self, context):
        super().__init__()
        self.context = context
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(60, 60)

        self.setAcceptDrops(True)

        self.dragging = False
        self.offset = QPoint()
        # --- 动画相关初始化 ---
        self.step = 0.0 # 动画步进 (0 ~ 2π)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)

        # 默认启动呼吸动画 (40ms 刷新一次，约 25帧，省资源且流畅)
        self.timer.start(40)

    def _update_animation(self):
        """定时器槽函数：更新呼吸状态"""
        self.step += 0.1
        if self.step > math.pi * 2:
            self.step = 0
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # --- 计算呼吸因子 ---
        breath_factor = (math.sin(self.step) + 1) / 2

        # --- 效果 1: 忽大忽小 (半径变化) ---
        base_radius = 22
        current_radius = base_radius + (6 * breath_factor)

        # --- 效果 2: 发光 (颜色/透明度变化) ---
        r_val = 74 + (40 * breath_factor)
        g_val = 144 + (40 * breath_factor)
        b_val = 226
        alpha_val = 200 + (55 * breath_factor)

        center_color = QColor(int(r_val), int(g_val), int(b_val), int(alpha_val))
        edge_color = QColor(52, 100, 158, 200)

        # --- 绘制球体 ---
        g = QRadialGradient(30, 30, current_radius)
        g.setColorAt(0, center_color)
        g.setColorAt(1, edge_color)
        p.setBrush(g)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPoint(30, 30), current_radius, current_radius)

        # --- 绘制图标/文字 ---
        p.setPen(Qt.white)
        font_size = 20 + (2 * breath_factor)
        p.setFont(QFont('Arial', int(font_size), QFont.Bold))
        p.drawText(self.rect(), Qt.AlignCenter, '💡')

    # --- 拖拽接收逻辑 ---
    def dragEnterEvent(self, e):
        if e.mimeData().hasText():
            e.accept()
            self.step = math.pi / 2
            self.update()
        else:
            e.ignore()

    def dropEvent(self, e):
        text = e.mimeData().text()
        if text.strip():
            self.context.main_window.quick_add_idea(text) # Call through context
            e.acceptProposedAction()

    # --- 鼠标交互逻辑 ---
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = e.pos()
            self.timer.stop()
            self.update()

    def mouseMoveEvent(self, e):
        if self.dragging:
            self.move(self.mapToGlobal(e.pos() - self.offset))

    def mouseReleaseEvent(self, e):
        if self.dragging:
            self.dragging = False
            pos = self.pos()
            save_setting('floating_ball_pos', {'x': pos.x(), 'y': pos.y()})
        if not self.timer.isActive():
            self.timer.start(40)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            # 双击打开新的主窗口
            self.context.show_clipboard_window()
            self.double_clicked.emit()

    def contextMenuEvent(self, e):
        m = QMenu(self)
        m.setStyleSheet("background:#2d2d2d;color:white;border:1px solid #333")
        m.addAction('📖 打开主窗口', self.context.show_clipboard_window)
        m.addAction('🗃️ 数据管理', self.context.show_main_window)
        m.addAction('➕ 新建灵感', self.context.new_idea)
        m.addSeparator()
        m.addAction('❌ 退出', self.context.quit_app)
        m.exec_(e.globalPos())
