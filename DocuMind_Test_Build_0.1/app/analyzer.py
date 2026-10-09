from pathlib import Path
from app.rules_engine import RulesEngine

class DocumentAnalyzer:
    def __init__(self, rules_path=None):
        if rules_path is None:
            rules_path = Path.home() / "AppData" / "Local" / "DocuMind" / "rules.json"
        self.engine = RulesEngine(rules_path)

    def analyze(self, text, file_name=""):
        result = self.engine.analyze(text)
        fields = result["fields"]
        summary_parts = []
        for key in ("document_type", "organization", "document_number", "document_date"):
            if fields.get(key):
                summary_parts.append(f"{key}: {fields[key]}")
        summary = "; ".join(summary_parts) if summary_parts else (text.strip().replace("\n", " ")[:350])
        return {
            "fields": fields,
            "matches": result["matches"],
            "unmatched_fields": result["unmatched_fields"],
            "summary": summary,
            "file_name": file_name,
        }
