# K Main_V3.py
import sys
import time
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QObject
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

# --- Refactored Imports ---
# Core Infrastructure
from core.logger import setup_logging
from core.settings import load_setting

# Data Layer
from data.db_manager import get_db_connection, close_db_connection
from data.repositories.idea_repository import IdeaRepository
from data.repositories.tag_repository import TagRepository
from data.repositories.category_repository import CategoryRepository

# Service Layer
from services.idea_service import IdeaService
from services.clipboard_service import ClipboardService
from services.hash_calculator import HashCalculator

# UI Layer
from ui.quick_window import QuickWindow
from ui.main_window import MainWindow
from ui.ball import FloatingBall

SERVER_NAME = "K_KUAIJIBIJI_SINGLE_INSTANCE_SERVER"

class AppManager(QObject):
    """
    应用程序管理器，负责协调各个UI组件的生命周期和交互。
    """
    def __init__(self, app, idea_service, clipboard_service):
        super().__init__()
        self.app = app
        # --- Dependency Injection ---
        self.idea_service = idea_service
        self.clipboard_service = clipboard_service
        # ---
        self.main_window = None
        self.quick_window = None
        self.ball = None

    def start(self):
        """创建所有核心组件并启动应用"""
        # 1. 创建 MainWindow，它需要 IdeaService
        self.main_window = MainWindow(self.idea_service)
        self.main_window.closing.connect(self.on_main_window_closing)

        # 2. 创建悬浮球
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

        # 3. 创建 QuickWindow，它需要 IdeaService 和 ClipboardService
        # (Note: The constructor for QuickWindow will be updated later)
        self.quick_window = QuickWindow(self.idea_service, self.clipboard_service)
        self.quick_window.open_main_window_requested.connect(self.show_main_window)

    def show_quick_window(self):
        """显示快速笔记窗口并置于顶层"""
        if self.quick_window:
            if self.quick_window.isMinimized():
                self.quick_window.showNormal()
            self.quick_window.show()
            self.quick_window.activateWindow()

    def show_main_window(self):
        """显示主数据管理窗口并置于顶层"""
        if self.main_window:
            if self.main_window.isMinimized():
                self.main_window.showNormal()
            self.main_window.show()
            self.main_window.activateWindow()

    def on_main_window_closing(self):
        if self.main_window:
            self.main_window.hide()
            
    def quit_application(self):
        """退出整个应用程序"""
        print("ℹ️  应用程序正在退出...")
        self.app.quit()

def main():
    """主函数入口"""
    setup_logging()
    app = QApplication(sys.argv)
    
    # --- 单例应用检测 (健壮版本) ---
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)

    if socket.waitForConnected(500):
        print("ℹ️  检测到已运行实例，发送 'SHOW' 指令并退出...")
        socket.write(b'SHOW')
        socket.flush()
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        sys.exit(0) # 正常退出新实例
    else:
        # 清理可能残留的服务器，防止僵尸进程
        QLocalServer.removeServer(SERVER_NAME)

    server = QLocalServer()
    if not server.listen(SERVER_NAME):
        QMessageBox.warning(None, "错误", f"无法创建单例服务: {server.errorString()}.")

    # --- 依赖注入容器设置 ---
    try:
        db_conn = get_db_connection()
    except Exception as e:
        QMessageBox.critical(None, "数据库错误", f"数据库初始化失败: {e}\n应用即将退出。")
        sys.exit(1)

    # 1. 实例化 Repositories
    idea_repo = IdeaRepository(db_conn)
    tag_repo = TagRepository(db_conn)
    category_repo = CategoryRepository(db_conn)

    # 2. 实例化 Services
    hash_calculator = HashCalculator()
    idea_service = IdeaService(idea_repo, tag_repo, category_repo)
    clipboard_service = ClipboardService(idea_repo, tag_repo, hash_calculator)
    
    # 确保在应用退出时关闭数据库连接
    app.aboutToQuit.connect(close_db_connection)

    # --- 启动应用 ---
    manager = AppManager(app, idea_service, clipboard_service)

    def handle_new_connection():
        conn = server.nextPendingConnection()
        if conn and conn.waitForReadyRead(500):
            msg = conn.readAll().data().decode()
            if msg == 'SHOW':
                manager.show_quick_window()

    server.newConnection.connect(handle_new_connection)
    
    manager.start()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
