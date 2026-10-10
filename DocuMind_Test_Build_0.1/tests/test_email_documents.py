import tempfile
import unittest
from pathlib import Path
from app.document_service import DocumentService
from app.scanner import scan_folders, SUPPORTED
from app.analyzer import DocumentAnalyzer

class EmailDocumentTests(unittest.TestCase):
    def test_scanner_supports_email_formats(self):
        self.assertIn('.eml', SUPPORTED)
        self.assertIn('.msg', SUPPORTED)

    def test_read_eml_headers_and_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'letter.eml'
            p.write_bytes(b'From: sender@example.com\r\nTo: office@example.com\r\nSubject: Test request\r\nDate: Mon, 05 Oct 2026 10:00:00 +0000\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nPlease confirm the delivery date by 15.10.2026.')
            doc = DocumentService(ocr_enabled=False).read(p)
            self.assertEqual(doc.status, 'ok', doc.error)
            self.assertIn('Please confirm', doc.text)
            self.assertEqual(doc.metadata['sender'], 'sender@example.com')
            self.assertEqual(doc.metadata['subject'], 'Test request')

    def test_analyzer_keeps_full_text_and_extracts_action_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            analyzer = DocumentAnalyzer(Path(tmp) / 'rules.json')
            source = 'Тема: Согласование\nПросим подтвердить дату поставки до 15.10.2026.'
            result = analyzer.analyze(source, 'letter.eml', metadata={'sender':'ООО Пример','subject':'Согласование'})
            self.assertEqual(result['full_text'], source)
            self.assertTrue(result['required_actions'])
            self.assertTrue(result['sender'])

if __name__ == '__main__':
    unittest.main()
