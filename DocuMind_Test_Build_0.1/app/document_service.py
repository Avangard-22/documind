from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

@dataclass
class DocumentData:
    file_path: str
    file_name: str
    file_type: str
    file_size: int
    modified_at: str
    status: str
    text: str = ""
    error: str = ""

    @property
    def text_length(self):
        return len(self.text)

class DocumentService:
    def read(self, path):
        path = Path(path)
        stat = path.stat()
        base = dict(
            file_path=str(path.resolve()),
            file_name=path.name,
            file_type=path.suffix.lower().lstrip("."),
            file_size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        )
        try:
            suffix = path.suffix.lower()
            if suffix == ".pdf":
                text = self._read_pdf(path)
            elif suffix == ".docx":
                text = self._read_docx(path)
            elif suffix == ".xlsx":
                text = self._read_xlsx(path)
            else:
                raise ValueError(f"Формат не поддерживается: {suffix}")
            return DocumentData(**base, status="ok", text=text)
        except Exception as exc:
            logger.exception("Не удалось прочитать %s", path)
            return DocumentData(**base, status="error", error=f"{type(exc).__name__}: {exc}")

    @staticmethod
    def _read_pdf(path):
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("Не установлен PyMuPDF. Установите зависимости из requirements.txt.") from exc
        chunks = []
        with fitz.open(path) as doc:
            for page in doc:
                chunks.append(page.get_text("text"))
        return "\n".join(chunks)

    @staticmethod
    def _read_docx(path):
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError("Не установлен python-docx. Установите зависимости из requirements.txt.") from exc
        doc = Document(path)
        chunks = [p.text for p in doc.paragraphs if p.text]
        for table in doc.tables:
            for row in table.rows:
                chunks.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(chunks)

    @staticmethod
    def _read_xlsx(path):
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise RuntimeError("Не установлен openpyxl. Установите зависимости из requirements.txt.") from exc
        chunks = []
        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            for ws in wb.worksheets:
                chunks.append(f"[Лист: {ws.title}]")
                for row in ws.iter_rows(values_only=True):
                    values = [str(v) for v in row if v is not None]
                    if values:
                        chunks.append(" | ".join(values))
        finally:
            wb.close()
        return "\n".join(chunks)
