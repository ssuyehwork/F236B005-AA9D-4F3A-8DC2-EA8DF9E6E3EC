# K Main_V3.py
import sys
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

# 导入窗口和数据库管理器
from ui.quick_window import QuickWindow
from ui.main_window import MainWindow
from ui.ball import FloatingBall
from data.db_manager import DatabaseManager
from core.settings import load_setting

SERVER_NAME = "K_KUAIJIBIJI_SINGLE_INSTANCE_SERVER"

class AppManager(QObject):
    """
    应用程序管理器，负责协调 QuickWindow 和 MainWindow 的生命周期。
    """
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.db_manager = None
        self.main_window = None
        self.quick_window = None
        self.ball = None

    def start(self):
        """初始化数据库、创建并显示悬浮球"""
        try:
            self.db_manager = DatabaseManager()
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            sys.exit(1)

        # 创建并显示悬浮球
        self.ball = FloatingBall() # 悬浮球不再需要主窗口实例
        self.ball.request_show_quick_window.connect(self.show_quick_window)
        self.ball.double_clicked.connect(self.show_quick_window)
        self.ball.request_show_main_window.connect(self.show_main_window)
        self.ball.request_quit_app.connect(self.quit_application)
        self.ball.new_idea_requested.connect(self._on_new_idea_requested)
        self.ball.quick_add_requested.connect(self._on_quick_add_requested)
        
        # 恢复悬浮球位置
        ball_pos = load_setting('floating_ball_pos')
        if ball_pos and isinstance(ball_pos, dict) and 'x' in ball_pos and 'y' in ball_pos:
            self.ball.move(ball_pos['x'], ball_pos['y'])
        else:
            g = QApplication.desktop().screenGeometry()
            self.ball.move(g.width()-80, g.height()//2)
            
        self.ball.show()

    def show_quick_window(self):
        """如果快速笔记窗口不存在则创建，然后显示"""
        if self.quick_window is None:
            self.quick_window = QuickWindow(self.db_manager)
            self.quick_window.open_main_window_requested.connect(self.show_main_window)
            self.quick_window.destroyed.connect(self._on_quick_window_destroyed)

        if self.quick_window.isMinimized():
            self.quick_window.showNormal()
        self.quick_window.show()
        self.quick_window.activateWindow()

    def _on_quick_window_destroyed(self):
        """当快速笔记窗口被销毁时，重置实例变量"""
        self.quick_window = None
        if self.main_window is None:
            self.quit_application()

    def show_main_window(self):
        """如果主窗口不存在则创建，然后显示"""
        if self.main_window is None:
            self.main_window = MainWindow()
            # 注意：主窗口现在没有自定义信号需要连接，因为它会自行销毁
            self.main_window.destroyed.connect(self._on_main_window_destroyed)

        if self.main_window.isMinimized():
            self.main_window.showNormal()
        self.main_window.show()
        self.main_window.activateWindow()

    def _on_main_window_destroyed(self):
        """当主窗口被销毁时，重置实例变量"""
        self.main_window = None
        if self.quick_window is None:
            self.quit_application()

    def _on_new_idea_requested(self):
        """响应悬浮球的新建笔记请求"""
        self.show_main_window() # 确保主窗口存在
        self.main_window.new_idea()

    def _on_quick_add_requested(self, text):
        """响应悬浮球的快速添加笔记请求"""
        self.show_main_window() # 确保主窗口存在
        self.main_window.quick_add_idea(text)
            
    def quit_application(self):
        """退出整个应用程序"""
        # 在这里可以添加清理逻辑，例如保存状态
        print("ℹ️  应用程序正在退出...")
        if self.ball:
            self.ball.close()
        self.app.quit()

def main():
    """主函数入口"""
    app = QApplication(sys.argv)
    
    # --- 单例应用检测 ---
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)

    # 如果能连接上服务器，说明已有实例在运行
    if socket.waitForConnected(500):
        print("ℹ️  检测到旧实例，发送退出指令...")
        # 发送 "EXIT" 消息给正在运行的实例
        socket.write(b'EXIT')
        socket.flush()
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        
        # 等待旧实例退出
        print("⏳ 等待旧实例退出...")
        time.sleep(0.5)
        
        # 清理可能残留的服务器，确保新实例可以监听
        QLocalServer.removeServer(SERVER_NAME)
        print("✅ 旧实例已清理")
    else:
        # 如果连接不上，也清理一下，以防有僵尸服务器
        QLocalServer.removeServer(SERVER_NAME)

    # 创建新的服务器（即当前实例）
    server = QLocalServer()
    if not server.listen(SERVER_NAME):
        print(f"❌ 无法创建单例服务器: {server.errorString()}")
        # 即使无法创建服务器，也继续运行，只是单例功能失效
    
    # --- 启动应用 ---
    manager = AppManager(app)

    def handle_new_connection():
        """处理来自新实例的连接"""
        conn = server.nextPendingConnection()
        if conn and conn.waitForReadyRead(500):
            msg = conn.readAll().data().decode()
            if msg == 'SHOW':
                # 显示并激活快速笔记窗口
                manager.show_quick_window()
            elif msg == 'EXIT':
                print("ℹ️  收到退出指令，准备退出...")
                manager.quit_application()

    server.newConnection.connect(handle_new_connection)
    
    manager.start()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
