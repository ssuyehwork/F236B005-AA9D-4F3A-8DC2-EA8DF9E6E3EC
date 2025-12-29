# data/db_manager.py
import sqlite3
from core.config import DB_NAME

class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self._init_schema()

    def _init_schema(self):
        c = self.conn.cursor()

        # 1. Ideas Table
        c.execute('''CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, content TEXT, color TEXT DEFAULT '#4a90e2',
            is_pinned INTEGER DEFAULT 0, is_favorite INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            category_id INTEGER, is_deleted INTEGER DEFAULT 0
        )''')

        # 2. Tags Table
        c.execute('CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)')

        # 3. Categories Table (Updated)
        c.execute('''CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER,
            color TEXT DEFAULT "#808080",
            sort_order INTEGER DEFAULT 0
        )''')

        # 4. Idea_Tags Table
        c.execute('CREATE TABLE IF NOT EXISTS idea_tags (idea_id INTEGER, tag_id INTEGER, PRIMARY KEY (idea_id, tag_id))')

        # --- Migrations ---
        c.execute("PRAGMA table_info(ideas)")
        idea_cols = [i[1] for i in c.fetchall()]
        if 'category_id' not in idea_cols:
            try: c.execute('ALTER TABLE ideas ADD COLUMN category_id INTEGER')
            except: pass
        if 'is_deleted' not in idea_cols:
            try: c.execute('ALTER TABLE ideas ADD COLUMN is_deleted INTEGER DEFAULT 0')
            except: pass

        c.execute("PRAGMA table_info(categories)")
        cat_cols = [i[1] for i in c.fetchall()]
        if 'sort_order' not in cat_cols:
            try: c.execute('ALTER TABLE categories ADD COLUMN sort_order INTEGER DEFAULT 0')
            except: pass

        self.conn.commit()

    # --- Idea CRUD ---
    def add_idea(self, title, content, color, tags, cat_id):
        c = self.conn.cursor()
        c.execute('INSERT INTO ideas (title, content, color, category_id) VALUES (?,?,?,?)', (title, content, color, cat_id))
        iid = c.lastrowid
        self._update_tags(iid, tags)
        self.conn.commit()
        return iid

    def update_idea(self, iid, title, content, color, tags, cat_id):
        c = self.conn.cursor()
        c.execute('UPDATE ideas SET title=?, content=?, color=?, category_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?', (title, content, color, cat_id, iid))
        self._update_tags(iid, tags)
        self.conn.commit()

    def _update_tags(self, iid, tags):
        c = self.conn.cursor()
        c.execute('DELETE FROM idea_tags WHERE idea_id=?', (iid,))
        for t in tags:
            t = t.strip()
            if t:
                c.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (t,))
                c.execute('SELECT id FROM tags WHERE name=?', (t,))
                tid = c.fetchone()[0]
                c.execute('INSERT INTO idea_tags VALUES (?,?)', (iid, tid))

    # --- State Management ---
    def toggle_field(self, iid, field):
        # ... (identical)
        pass

    def set_deleted(self, iid, state):
        # ... (identical)
        pass

    def move_category(self, iid, cat_id):
        # ... (identical)
        pass

    def delete_permanent(self, iid):
        # ... (identical)
        pass

    # --- Queries ---
    def get_idea(self, iid):
        # ... (identical)
        pass

    def get_ideas(self, search, f_type, f_val):
        # ... (identical)
        pass

    def get_tags(self, iid):
        # ... (identical)
        pass

    # --- Categories ---
    def get_categories(self):
        """获取所有分类，并按层级和顺序排序"""
        c = self.conn.cursor()
        # Order by parent_id first, then by the custom sort_order
        c.execute('SELECT * FROM categories ORDER BY parent_id, sort_order')
        return c.fetchall()

    def add_category(self, name, parent_id=None):
        """添加新分类（组或区）"""
        c = self.conn.cursor()
        c.execute('INSERT INTO categories (name, parent_id) VALUES (?, ?)', (name, parent_id))
        self.conn.commit()

    def rename_category(self, cat_id, new_name):
        # ... (identical)
        pass

    def delete_category(self, cid):
        # ... (identical)
        pass

    def update_category_structure(self, cat_id, new_parent_id, new_sort_order):
        """更新一个分类的父级和排序"""
        c = self.conn.cursor()
        c.execute('UPDATE categories SET parent_id = ?, sort_order = ? WHERE id = ?', (new_parent_id, new_sort_order, cat_id))
        self.conn.commit()

    def get_counts(self):
        # ... (identical)
        pass

    def get_top_tags(self):
        # ... (identical)
        pass
