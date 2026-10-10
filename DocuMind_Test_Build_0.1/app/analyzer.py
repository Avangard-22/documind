from pathlib import Path
import re
from app.rules_engine import RulesEngine

class DocumentAnalyzer:
    """Rule-based extraction plus conservative correspondence heuristics.

    This release does not claim to contain a language model. An LLM provider can be
    added behind this interface later without changing the pipeline or Excel writer.
    """
    def __init__(self, rules_path=None):
        if rules_path is None:
            import os
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            rules_path = base / "DocuMind" / "rules.json"
        self.engine = RulesEngine(rules_path)

    @staticmethod
    def _first(patterns, text):
        for pattern in patterns:
            match = re.search(pattern, text, re.I | re.M)
            if match:
                return match.group(1).strip(" \t:;,.\r\n")
        return ""

    def analyze(self, text, file_name="", metadata=None): 
        metadata = metadata or {}
        result = self.engine.analyze(text)
        fields = result["fields"]
        sender = metadata.get("sender", "") or self._first([r"^Отправитель\s*[:：]\s*(.+)$", r"^От\s*[:：]\s*(.+)$"], text)
        recipient = metadata.get("recipient", "") or self._first([r"^Получатель\s*[:：]\s*(.+)$", r"^Кому\s*[:：]\s*(.+)$"], text)
        subject = metadata.get("subject", "") or self._first([r"^Тема\s*[:：]\s*(.+)$", r"^Subject\s*[:：]\s*(.+)$"], text)
        doc_date = fields.get("document_date", "") or metadata.get("email_date", "")
        number = fields.get("document_number", "")
        contract = fields.get("contract_number", "")
        body = re.sub(r"\s+", " ", text).strip()
        summary = body[:600] + ("…" if len(body) > 600 else "")
        action_lines = []
        deadline = ""
        for line in text.splitlines():
            clean = line.strip()
            if clean and re.search(r"\b(просим|необходимо|требуется|просим вас|обязаны|предлагаем|подтвердить|направить|предоставить|согласовать|оплатить|ответить)\b", clean, re.I):
                action_lines.append(clean[:500])
            if not deadline and re.search(r"\b(до|не позднее|срок|к)\s+\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", clean, re.I):
                deadline = self._first([r"\b(?:до|не позднее|срок|к)\s+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})"], clean)
        if not summary:
            summary = "; ".join(f"{k}: {fields[k]}" for k in ("document_type", "organization", "document_number", "document_date") if fields.get(k))
        doc_type = fields.get("document_type", "")
        if not doc_type:
            doc_type = "Электронное письмо" if metadata.get("subject") or metadata.get("sender") else "Документ"
        needs_reply = bool(re.search(r"\b(просим ответить|просим сообщить|ждём ответа|ожидаем ответа|просим подтвердить|ответить до)\b", text, re.I))
        # Heuristic confidence is intentionally not presented as calibrated probability.
        confidence = "medium" if (sender or subject or number or doc_date) else "low"
        review_required = confidence == "low" or bool(result["unmatched_fields"])
        return {
            "fields": fields, "matches": result["matches"], "unmatched_fields": result["unmatched_fields"],
            "summary": summary, "file_name": file_name, "full_text": text,
            "metadata": metadata, "sender": sender, "recipient": recipient, "subject": subject,
            "document_type": doc_type, "document_number": number, "document_date": doc_date,
            "contract_number": contract, "required_actions": action_lines, "deadline": deadline,
            "needs_reply": needs_reply, "confidence": confidence, "review_required": review_required,
        }   
