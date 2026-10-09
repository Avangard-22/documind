from __future__ import annotations
import json, os, re, shutil, tempfile
from datetime import datetime
from pathlib import Path

DEFAULT_RULES = {
    "version": 1,
    "fields": [
        {"name":"document_number","label":"Номер документа","enabled":True,"patterns":[r"(?im)^\s*(?:номер документа|номер|№)\s*[:№]?\s*([A-ZА-ЯЁ0-9][A-ZА-ЯЁ0-9./_-]*)"]},
        {"name":"document_date","label":"Дата документа","enabled":True,"patterns":[r"(?im)^\s*(?:дата документа|дата)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2})"]},
        {"name":"organization","label":"Организация","enabled":True,"patterns":[r"(?im)^\s*(?:организация|контрагент|поставщик)\s*[:\-]\s*(.+?)\s*$"]},
        {"name":"document_type","label":"Тип документа","enabled":True,"patterns":[r"(?im)^\s*(?:тип документа|вид документа)\s*[:\-]\s*(.+?)\s*$"]},
        {"name":"inn","label":"ИНН","enabled":True,"patterns":[r"(?im)\bИНН\s*[:№]?\s*(\d{10}|\d{12})\b"]},
        {"name":"contract_number","label":"Номер договора","enabled":True,"patterns":[r"(?im)^\s*(?:номер договора|договор №|договор)\s*[:№]?\s*([A-ZА-ЯЁ0-9][A-ZА-ЯЁ0-9./_-]*)"]},
    ],
}

class RulesEngine:
    MAX_FILE_SIZE = 2 * 1024 * 1024
    def __init__(self, rules_path):
        self.rules_path = Path(rules_path)
        self.rules = {}
        self.load_rules()

    def load_rules(self):
        self.rules_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.rules_path.exists():
            self._atomic_write(DEFAULT_RULES)
        if self.rules_path.stat().st_size > self.MAX_FILE_SIZE:
            raise ValueError("Файл правил слишком большой.")
        with self.rules_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.validate(data)
        self.rules = data
        return self.rules

    def get_rules(self):
        return json.loads(json.dumps(self.rules, ensure_ascii=False))

    def validate(self, data):
        if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("fields"), list):
            raise ValueError("Некорректная структура правил (ожидается version=1 и fields).")
        if len(data["fields"]) > 200:
            raise ValueError("Слишком много полей.")
        names = set()
        for i, field in enumerate(data["fields"], 1):
            if not isinstance(field, dict):
                raise ValueError(f"Правило #{i} должно быть объектом.")
            name, label, enabled, patterns = field.get("name"), field.get("label"), field.get("enabled"), field.get("patterns")
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,99}", name):
                raise ValueError(f"Правило #{i}: неверное имя поля.")
            if name in names:
                raise ValueError(f"Повторяется имя поля: {name}")
            names.add(name)
            if not isinstance(label, str) or not label.strip() or not isinstance(enabled, bool) or not isinstance(patterns, list):
                raise ValueError(f"Правило {name}: неверные label/enabled/patterns.")
            if len(patterns) > 50:
                raise ValueError(f"Правило {name}: слишком много шаблонов.")
            for pattern in patterns:
                if not isinstance(pattern, str) or not pattern or len(pattern) > 1000:
                    raise ValueError(f"Правило {name}: шаблон пуст или слишком длинный.")
                try:
                    re.compile(pattern)
                except re.error as exc:
                    raise ValueError(f"Ошибка шаблона {name}: {exc}") from exc

    def _atomic_write(self, data):
        self.rules_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.rules_path.parent, suffix=".tmp", delete=False) as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
                tmp = Path(f.name)
            tmp.replace(self.rules_path)
        except Exception:
            if tmp:
                tmp.unlink(missing_ok=True)
            raise

    def save_rules(self, data):
        self.validate(data)
        if self.rules_path.exists():
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = self.rules_path.with_name(f"{self.rules_path.stem}.{stamp}.bak")
            shutil.copy2(self.rules_path, backup)
        self._atomic_write(data)
        self.rules = self.get_rules_from(data)

    @staticmethod
    def get_rules_from(data):
        return json.loads(json.dumps(data, ensure_ascii=False))

    def analyze(self, text):
        if not isinstance(text, str):
            raise TypeError("Текст документа должен быть строкой.")
        if len(text) > 10_000_000:
            raise ValueError("Текст слишком большой для анализа.")
        fields, matches, unmatched = {}, [], []
        for field in self.rules["fields"]:
            if not field["enabled"]:
                continue
            found = None
            for pattern in field["patterns"]:
                match = re.search(pattern, text)
                if match:
                    value = (match.group(1) if match.lastindex else match.group(0)).strip()
                    if value:
                        found = (value, match.group(0).strip())
                        break
            if found:
                fields[field["name"]] = found[0]
                matches.append({"name":field["name"],"label":field["label"],"value":found[0],"source_text":found[1]})
            else:
                unmatched.append(field["name"])
        return {"fields":fields, "matches":matches, "unmatched_fields":unmatched}

    def test_pattern(self, pattern, sample):
        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            return {"success":False,"error":str(exc),"matches":[]}
        result = []
        for match in compiled.finditer(sample):
            result.append({"value":(match.group(1) if match.lastindex else match.group(0)).strip(),"source_text":match.group(0).strip(),"start":match.start(),"end":match.end()})
            if len(result) >= 100:
                break
        return {"success":True,"error":None,"matches":result}
