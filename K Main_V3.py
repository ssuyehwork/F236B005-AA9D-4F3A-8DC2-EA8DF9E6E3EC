# K Main_V3.py
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

# 导入窗口和数据库管理器
from ui.quick_window import QuickWindow
from ui.main_window import MainWindow
from data.db_manager import DatabaseManager

SERVER_NAME = "K_RAPIDNOTES_SINGLE_INSTANCE_SERVER"

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

    def start(self):
        """初始化数据库并启动主窗口 (QuickWindow)"""
        try:
            self.db_manager = DatabaseManager()
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            # 在这里可以显示一个错误对话框
            sys.exit(1)

        self.quick_window = QuickWindow(self.db_manager)
        self.quick_window.open_main_window_requested.connect(self.show_main_window)
        self.quick_window.show()

    def show_main_window(self):
        """创建或显示主数据管理窗口"""
        if self.main_window is None:
            self.main_window = MainWindow() # MainWindow 不需要 db_manager 参数
            self.main_window.closing.connect(self.on_main_window_closing)

        # 如果窗口被最小化了，恢复它
        if self.main_window.isMinimized():
            self.main_window.showNormal()
        self.main_window.show()
        self.main_window.activateWindow() # 将窗口带到前台

    def on_main_window_closing(self):
        """
        处理 MainWindow 的关闭事件。
        目前只是隐藏窗口，应用生命周期由 QuickWindow 控制。
        """
        if self.main_window:
            self.main_window.hide()

def main():
    """主函数入口"""
    app = QApplication(sys.argv)

    # --- 单例应用检测 ---
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)

    # 如果能连接上服务器，说明已有实例在运行
    if socket.waitForConnected(500):
        # 发送一个 "SHOW" 消息给正在运行的实例
        socket.write(b'SHOW')
        socket.flush()
        socket.waitForBytesWritten()
        socket.disconnectFromServer()
        print("ℹ️  应用已在运行，已发送显示请求。正在退出...")
        return # 退出当前实例

    # 没有现有实例，则创建服务器
    server = QLocalServer()
    # 清理可能残留的服务器文件
    QLocalServer.removeServer(SERVER_NAME)
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
            if msg == 'SHOW' and manager.quick_window:
                # 显示并激活主窗口
                manager.quick_window.showNormal()
                manager.quick_window.activateWindow()

    server.newConnection.connect(handle_new_connection)

    manager.start()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
