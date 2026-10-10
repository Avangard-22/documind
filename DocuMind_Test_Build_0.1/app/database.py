import hashlib, json, sqlite3
from pathlib import Path
from datetime import datetime, timezone

class DocuMindDatabase:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY,
                    file_path TEXT NOT NULL UNIQUE,
                    file_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    modified_at TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT NOT NULL DEFAULT '',
                    analysis_json TEXT NOT NULL DEFAULT '{}',
                    full_text TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    processed_at TEXT NOT NULL
                )
            """)
            # Lightweight forward-compatible migration for existing v0.1 databases.
            columns = {row[1] for row in c.execute("PRAGMA table_info(documents)").fetchall()}
            if "full_text" not in columns:
                c.execute("ALTER TABLE documents ADD COLUMN full_text TEXT NOT NULL DEFAULT ''")
            if "metadata_json" not in columns:
                c.execute("ALTER TABLE documents ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'")
            c.execute("CREATE INDEX IF NOT EXISTS idx_documents_sha256 ON documents(sha256)")

    @staticmethod
    def calculate_sha256(path):
        digest = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def find_by_path(self, path):
        with self._connect() as c:
            row = c.execute("SELECT * FROM documents WHERE file_path=?", (str(Path(path).resolve()),)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["analysis"] = json.loads(result.pop("analysis_json") or "{}")
        result["metadata"] = json.loads(result.pop("metadata_json", "{}") or "{}")
        return result

    def save_document(self, record):
        now = datetime.now(timezone.utc).isoformat()
        values = (
            str(Path(record["file_path"]).resolve()), record["file_name"], record["file_type"],
            int(record["file_size"]), record["modified_at"], record.get("sha256", ""),
            record.get("status", "ok"), record.get("error", ""),
            json.dumps(record.get("analysis", {}), ensure_ascii=False), record.get("full_text", ""),
            json.dumps(record.get("metadata", {}), ensure_ascii=False), now
        )
        with self._connect() as c:
            c.execute("""
                INSERT INTO documents(file_path,file_name,file_type,file_size,modified_at,sha256,status,error,analysis_json,full_text,metadata_json,processed_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_name=excluded.file_name, file_type=excluded.file_type,
                    file_size=excluded.file_size, modified_at=excluded.modified_at,
                    sha256=excluded.sha256, status=excluded.status, error=excluded.error,
                    analysis_json=excluded.analysis_json, full_text=excluded.full_text,
                    metadata_json=excluded.metadata_json, processed_at=excluded.processed_at
            """, values)
        return self.find_by_path(record["file_path"])

    def list_documents(self, limit=1000):
        with self._connect() as c:
            rows = c.execute("SELECT * FROM documents ORDER BY processed_at DESC LIMIT ?", (limit,)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["analysis"] = json.loads(item.pop("analysis_json") or "{}")
            item["metadata"] = json.loads(item.pop("metadata_json", "{}") or "{}")
            result.append(item)
        return result
  
