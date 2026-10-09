import tempfile, unittest
from pathlib import Path
from app.scanner import scan_folders

class ScannerTests(unittest.TestCase):
    def test_supported_extensions(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/"a.pdf").write_bytes(b"x"); (root/"b.docx").write_bytes(b"x")
            (root/"c.doc").write_bytes(b"x"); (root/"sub").mkdir(); (root/"sub"/"d.xlsx").write_bytes(b"x")
            found={p.name for p in scan_folders([root])}
            self.assertEqual(found,{"a.pdf","b.docx","d.xlsx"})

if __name__=="__main__":unittest.main()
