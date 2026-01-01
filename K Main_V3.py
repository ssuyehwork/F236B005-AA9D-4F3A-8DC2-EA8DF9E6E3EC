# K Main_V3.py
import sys
import time
import os
from PyQt5.QtWidgets import QApplication, QMenu, QSystemTrayIcon
from PyQt5.QtCore import QObject, Qt, QPoint
from PyQt5.QtGui import QIcon
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

from ui.quick_window import QuickWindow
from ui.main_window import MainWindow
from ui.ball import FloatingBall
from ui.action_popup import ActionPopup
from ui.common_tags_manager import CommonTagsManager
from ui.advanced_tag_selector import AdvancedTagSelector
from data.db_manager import DatabaseManager
from core.settings import load_setting

SERVER_NAME = "K_KUAIJIBIJI_SINGLE_INSTANCE_SERVER"

class AppManager(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.db_manager = None
        self.main_window = None
        self.quick_window = None
        self.ball = None
        self.popup = None 
        self.tray_icon = None # 新增托盘图标

    def start(self):
        try:
            self.db_manager = DatabaseManager()
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            sys.exit(1)

        # 【核心修改】设置全局应用图标 (任务栏图标)
        logo_path = os.path.join("assets", "logo.svg")
        if os.path.exists(logo_path):
            app_icon = QIcon(logo_path)
            self.app.setWindowIcon(app_icon)
        else:
            print("⚠️ 未找到 logo.svg，请确保文件在 assets 文件夹中")
            app_icon = QIcon() # 空图标防止报错

        # --- 初始化系统托盘 ---
        self._init_tray_icon(app_icon)

        self.main_window = MainWindow()
        self.main_window.closing.connect(self.on_main_window_closing)

        self.ball = FloatingBall(self.main_window)
        
        self.ball.request_show_quick_window.connect(self.show_quick_window)
        self.ball.double_clicked.connect(self.show_quick_window)
        self.ball.request_show_main_window.connect(self.show_main_window)
        self.ball.request_quit_app.connect(self.quit_application)
        
        ball_pos = load_setting('floating_ball_pos')
        if ball_pos and isinstance(ball_pos, dict) and 'x' in ball_pos and 'y' in ball_pos:
            self.ball.move(ball_pos['x'], ball_pos['y'])
        else:
            g = QApplication.desktop().screenGeometry()
            self.ball.move(g.width()-80, g.height()//2)
            
        self.ball.show()

        self.quick_window = QuickWindow(self.db_manager)
        self.quick_window.open_main_window_requested.connect(self.show_main_window)
        
        self.popup = ActionPopup() 
        self.popup.request_favorite.connect(self._handle_popup_favorite)
        # 切换标签信号
        self.popup.request_tag_toggle.connect(self._handle_popup_tag_toggle)
        self.popup.request_manager.connect(self._open_common_tags_manager)
        
        self.quick_window.cm.data_captured.connect(self._on_clipboard_data_captured)

    def _init_tray_icon(self, icon):
        """初始化系统托盘图标"""
        self.tray_icon = QSystemTrayIcon(self.app)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("RapidNotes 快速笔记")
        
        # 托盘右键菜单
        menu = QMenu()
        # 注意：系统托盘菜单样式通常受操作系统控制，Qt样式表可能不完全生效，但还是加上
        menu.setStyleSheet("""
            QMenu { background-color: #2D2D2D; color: #EEE; border: 1px solid #444; }
            QMenu::item { padding: 6px 24px; }
            QMenu::item:selected { background-color: #4a90e2; color: white; }
        """)
        
        action_show = menu.addAction("显示主界面")
        action_show.triggered.connect(self.show_main_window)
        
        action_quick = menu.addAction("显示快速笔记")
        action_quick.triggered.connect(self.show_quick_window)
        
        menu.addSeparator()
        
        action_quit = menu.addAction("退出程序")
        action_quit.triggered.connect(self.quit_application)
        
        self.tray_icon.setContextMenu(menu)
        
        # 左键点击托盘显示主界面
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        
        self.tray_icon.show()

    def _on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger: # 单击
            self.show_main_window()

    def _open_common_tags_manager(self):
        """打开常用标签管理界面"""
        dlg = CommonTagsManager()
        self._force_activate(dlg)
        if dlg.exec_():
            if self.popup:
                self.popup.common_tags_bar.reload_tags()

    def _on_clipboard_data_captured(self, idea_id):
        self.ball.trigger_clipboard_feedback()
        if self.popup:
            self.popup.show_at_mouse(idea_id)

    def _handle_popup_favorite(self, idea_id):
        self.db_manager.set_favorite(idea_id, True)
        if self.main_window.isVisible():
            self.main_window._load_data()
            self.main_window.sidebar.refresh()

    def _handle_popup_tag_toggle(self, idea_id, tag_name, checked):
        if checked:
            self.db_manager.add_tags_to_multiple_ideas([idea_id], [tag_name])
        else:
            self.db_manager.remove_tag_from_multiple_ideas([idea_id], tag_name)
            
        if self.main_window.isVisible():
            self.main_window._load_data()
            self.main_window._refresh_tag_panel()

    def _force_activate(self, window):
        if not window: return
        window.show()
        if window.isMinimized():
            window.setWindowState(window.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
            window.showNormal()
        window.raise_()
        window.activateWindow()

    def show_quick_window(self, pos=None):
        if not self.quick_window:
            return

        if pos and isinstance(pos, QPoint):
            screen_geometry = QApplication.desktop().screenGeometry(pos)
            win_size = self.quick_window.size()

            x = pos.x()
            y = pos.y()

            if x + win_size.width() > screen_geometry.right():
                x = screen_geometry.right() - win_size.width()

            if y + win_size.height() > screen_geometry.bottom():
                y = screen_geometry.bottom() - win_size.height()

            self.quick_window.move(x, y)

        self._force_activate(self.quick_window)


    def toggle_quick_window(self):
        if self.quick_window and self.quick_window.isVisible():
            self.quick_window.hide()
        else:
            self.show_quick_window()

    def show_main_window(self):
        self._force_activate(self.main_window)

    def on_main_window_closing(self):
        if self.main_window:
            self.main_window.hide()
            
    def quit_application(self):
        print("ℹ️  应用程序正在退出...")
        self.app.quit()

def main():
    app = QApplication(sys.argv)
    
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)

    if socket.waitForConnected(500):
        print("ℹ️  检测到旧实例，发送退出指令...")
        socket.write(b'EXIT')
        socket.flush()
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        time.sleep(0.5)
        QLocalServer.removeServer(SERVER_NAME)
        print("✅ 旧实例已清理")
    else:
        QLocalServer.removeServer(SERVER_NAME)

    server = QLocalServer()
    if not server.listen(SERVER_NAME):
        print(f"❌ 无法创建单例服务器: {server.errorString()}")
    
    manager = AppManager(app)

    def handle_new_connection():
        conn = server.nextPendingConnection()
        if conn and conn.waitForReadyRead(500):
            msg = conn.readAll().data().decode()
            if msg == 'SHOW':
                manager.show_quick_window()
            elif msg == 'EXIT':
                manager.quit_application()

    server.newConnection.connect(handle_new_connection)
    
    manager.start()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()