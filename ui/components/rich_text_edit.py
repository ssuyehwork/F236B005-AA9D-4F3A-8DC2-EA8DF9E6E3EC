# ui/components/rich_text_edit.py
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QImage, QTextImageFormat
from PyQt5.QtCore import Qt, QByteArray, QBuffer, QIODevice

class RichTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_data = None  # 用于暂存图片数据

    def canInsertFromMimeData(self, source):
        # 我们只关心图片
        return source.hasImage() or super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        if source.hasImage():
            image = source.imageData()
            if isinstance(image, QImage):
                # 将图片数据转换为字节并暂存
                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.WriteOnly)
                image.save(buffer, "PNG")  # 保存为PNG格式
                self.image_data = byte_array.data()

                # 在文本框中插入一个占位符
                self.insertPlainText("[图片]")
                return

        super().insertFromMimeData(source)

    def get_image_data(self):
        return self.image_data

    def set_image_data(self, data):
        self.image_data = data

    def clear_image_data(self):
        self.image_data = None
