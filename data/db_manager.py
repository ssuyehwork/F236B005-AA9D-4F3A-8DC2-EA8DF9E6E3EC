# data/db_manager.py
import sqlite3
import logging
from core.config import DB_NAME
from data.schema_migrations import SchemaMigration

logger = logging.getLogger(__name__)

_connection = None

def get_db_connection():
    """
    获取全局唯一的数据库连接。
    如果连接不存在，则创建并初始化它。
    """
    global _connection
    if _connection is None:
        try:
            logger.info(f"正在连接到数据库: {DB_NAME}")
            _connection = sqlite3.connect(DB_NAME)
            # 启用外键约束
            _connection.execute("PRAGMA foreign_keys = ON")
            
            # 应用数据库迁移
            SchemaMigration.apply(_connection)
            
            logger.info("数据库连接成功并完成初始化。")
        except sqlite3.Error as e:
            logger.exception(f"数据库连接失败: {e}")
            raise  # 重新引发异常，让应用知道启动失败

    return _connection

def close_db_connection():
    """关闭全局数据库连接"""
    global _connection
    if _connection:
        _connection.close()
        _connection = None
        logger.info("数据库连接已关闭。")
