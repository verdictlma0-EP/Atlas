import sqlite3
import json
import datetime

class Memory:
    """Single SQLite DB with provenance."""
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY,
                type TEXT,
                scope TEXT,
                key TEXT,
                value TEXT,
                source_type TEXT,
                embedding BLOB,
                metadata JSON,
                created_at TEXT
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_type_scope ON memories(type, scope)")
        conn.commit()
        conn.close()

    def store(self, mem_type, key, value, source_type, scope="global", metadata=None):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO memories (type, scope, key, value, source_type, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (mem_type, scope, key, value, source_type,
              json.dumps(metadata or {}), datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def retrieve(self, mem_type=None, scope=None, key=None):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        query = "SELECT key, value, source_type, metadata FROM memories WHERE 1=1"
        params = []
        if mem_type:
            query += " AND type = ?"
            params.append(mem_type)
        if scope:
            query += " AND scope = ?"
            params.append(scope)
        if key:
            query += " AND key LIKE ?"
            params.append(f"%{key}%")
        query += " ORDER BY created_at DESC LIMIT 10"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [{"key": r[0], "value": r[1], "source": r[2], "meta": json.loads(r[3] or "{}")} for r in rows]
