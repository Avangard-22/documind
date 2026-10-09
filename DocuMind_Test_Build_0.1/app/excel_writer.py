from pathlib import Path
import shutil
from datetime import datetime

HEADERS = [
    "Путь к документу", "Имя файла", "Формат", "Статус", "Дата обработки",
    "Номер документа", "Дата документа", "Организация", "ИНН",
    "Номер договора", "Тип документа", "Краткая выжимка", "Ошибка"
]
FIELD_MAP = {
    "Номер документа":"document_number", "Дата документа":"document_date",
    "Организация":"organization", "ИНН":"inn", "Номер договора":"contract_number",
    "Тип документа":"document_type",
}

class ExcelRegistryWriter:
    def append_results(self, output_path, records, create_if_missing=True, backup=True):
        from openpyxl import Workbook, load_workbook
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if backup:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                shutil.copy2(path, path.with_name(f"{path.stem}.{stamp}.bak{path.suffix}"))
            wb = load_workbook(path)
            ws = wb.active
            existing_headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
            if not existing_headers or all(v is None for v in existing_headers):
                ws.delete_rows(1, ws.max_row)
                ws.append(HEADERS)
                headers = HEADERS
            else:
                headers = existing_headers
                for header in HEADERS:
                    if header not in headers:
                        headers.append(header)
                        ws.cell(1, len(headers), header)
        else:
            if not create_if_missing:
                raise FileNotFoundError(path)
            wb = Workbook()
            ws = wb.active
            ws.title = "DocuMind"
            ws.append(HEADERS)
            headers = HEADERS[:]

        path_col = headers.index("Путь к документу") + 1 if "Путь к документу" in headers else None
        existing_rows = {}
        if path_col:
            for row_num in range(2, ws.max_row + 1):
                key = ws.cell(row_num, path_col).value
                if key:
                    existing_rows[str(Path(str(key)).resolve()).casefold()] = row_num

        added = 0
        for record in records:
            file_path = str(Path(record.get("file_path", "")).resolve())
            key = file_path.casefold()
            row_num = existing_rows.get(key)
            if row_num is None:
                row_num = ws.max_row + 1
                added += 1
                existing_rows[key] = row_num
            data = {
                "Путь к документу": file_path,
                "Имя файла": record.get("file_name", ""),
                "Формат": record.get("file_type", ""),
                "Статус": record.get("status", ""),
                "Дата обработки": record.get("processed_at", ""),
                "Краткая выжимка": record.get("summary", ""),
                "Ошибка": record.get("error", ""),
            }
            fields = record.get("fields", {})
            for header, field_name in FIELD_MAP.items():
                data[header] = fields.get(field_name, "")
            for col, header in enumerate(headers, 1):
                if header in data:
                    ws.cell(row_num, col, data[header])
        wb.save(path)
        wb.close()
        return added
