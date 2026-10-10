import tempfile
import unittest
from pathlib import Path
from app.database import DocuMindDatabase

class DatabaseMigrationTests(unittest.TestCase):
    def test_full_text_and_metadata_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = DocuMindDatabase(Path(tmp) / 'db.sqlite3')
            p = Path(tmp) / 'x.eml'; p.write_text('test', encoding='utf-8')
            db.save_document({'file_path':str(p), 'file_name':'x.eml', 'file_type':'eml', 'file_size':4,
                              'modified_at':'2026-10-01T00:00:00+00:00','sha256':'abc','status':'ok',
                              'analysis':{'summary':'summary'}, 'full_text':'full body', 'metadata':{'sender':'a@example.com'}})
            row = db.find_by_path(p)
            self.assertEqual(row['full_text'], 'full body')
            self.assertEqual(row['metadata']['sender'], 'a@example.com')

if __name__ == '__main__': unittest.main()
