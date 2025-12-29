# main.py
import sys
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

from ui.main_window import MainWindow
from ui.quick_window import QuickWindow

SERVER_NAME = "rapidnotes_pro_server"

class AppManager:
    """管理应用中的窗口实例和交互"""
    def __init__(self, app):
        self.app = app
        self.main_window = None
        self.quick_window = None

    def start(self):
        print("[DEBUG] 启动快速搜索窗口...")
        self.quick_window = QuickWindow()
        self.quick_window.open_main_window_requested.connect(self.show_main_window)
        self.quick_window.show()

    def show_main_window(self):
        print("[DEBUG] 请求打开主数据管理窗口...")
        if self.main_window is None or not self.main_window.isVisible():
            print("[DEBUG] 创建新的主窗口实例...")
            self.main_window = MainWindow()
            self.main_window.show()
        else:
            print("[DEBUG] 主窗口已存在，激活显示。")
            self.main_window.activateWindow()
            self.main_window.show()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 保持原有的单例应用逻辑不变
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)

    if socket.waitForConnected(500):
        print("[DEBUG] 检测到旧实例，退出当前实例。")
        # 这里可以简单退出，或者发送指令让旧实例显示 quick_window
        return
    else:
        QLocalServer.removeServer(SERVER_NAME)
        server = QLocalServer()
        if not server.listen(SERVER_NAME):
            print(f"[ERROR] 无法创建服务器: {server.errorString()}")

        # 启动应用
        print("[DEBUG] 创建应用管理器...")
        manager = AppManager(app)
        manager.start()

        print("[DEBUG] 应用程序启动完成")
        sys.exit(app.exec_())

if __name__ == '__main__':
    main()
