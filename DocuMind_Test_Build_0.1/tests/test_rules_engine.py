import tempfile, unittest
from pathlib import Path
from app.rules_engine import RulesEngine

class RulesEngineTests(unittest.TestCase):
    def test_default_rules_extract_fields(self):
        with tempfile.TemporaryDirectory() as d:
            engine=RulesEngine(Path(d)/"rules.json")
            result=engine.analyze("Номер документа: ДОГ-2026-015\nДата документа: 08.10.2026\nОрганизация: ООО Пример\nИНН: 1234567890")
            self.assertEqual(result["fields"]["document_number"],"ДОГ-2026-015")
            self.assertEqual(result["fields"]["document_date"],"08.10.2026")
            self.assertEqual(result["fields"]["organization"],"ООО Пример")
            self.assertEqual(result["fields"]["inn"],"1234567890")
    def test_invalid_regex_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            engine=RulesEngine(Path(d)/"rules.json")
            rules=engine.get_rules()
            rules["fields"][0]["patterns"]=["("]
            with self.assertRaises(ValueError):engine.validate(rules)
    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"rules.json"; engine=RulesEngine(path)
            rules=engine.get_rules(); rules["fields"][0]["enabled"]=False
            engine.save_rules(rules)
            self.assertFalse(RulesEngine(path).get_rules()["fields"][0]["enabled"])

if __name__=="__main__":unittest.main()
