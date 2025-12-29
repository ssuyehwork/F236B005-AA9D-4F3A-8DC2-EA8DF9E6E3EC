# -*- coding: utf-8 -*-
# K 快速笔记_V3.py

import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.clipboard_pro import ClipboardProWindow
from ui.ball import FloatingBall
from data.db_manager import DatabaseManager
from core.settings import load_setting

class AppContext:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.clipboard_window = ClipboardProWindow(self)
        self.main_window = MainWindow(self) # The old main window
        self.floating_ball = FloatingBall(self)

        # Hide the main window by default
        self.main_window.hide()

        # Load and apply floating ball position
        ball_pos = load_setting('floating_ball_pos')
        if ball_pos and isinstance(ball_pos, dict) and 'x' in ball_pos and 'y' in ball_pos:
            self.floating_ball.move(ball_pos['x'], ball_pos['y'])
        else:
            g = QApplication.desktop().screenGeometry()
            self.floating_ball.move(g.width()-80, g.height()//2)

        self.floating_ball.show()

    def show_clipboard_window(self):
        self.clipboard_window.show()

    def show_main_window(self):
        self.main_window.show()

    def new_idea(self):
        # This can be called from the ball's context menu
        self.main_window.new_idea()

    def quit_app(self):
        self.main_window.quit_app()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    context = AppContext()
    # By default, only the ball is shown. The user can double-click it to show the clipboard window.

    sys.exit(app.exec_())
