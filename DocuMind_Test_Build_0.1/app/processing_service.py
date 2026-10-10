from pathlib import Path
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class ProcessingService:
    def __init__(self, database, document_service=None, analyzer=None, excel_writer=None):
        from app.document_service import DocumentService
        from app.analyzer import DocumentAnalyzer
        from app.excel_writer import ExcelRegistryWriter
        self.database = database
        self.document_service = document_service or DocumentService()
        self.analyzer = analyzer or DocumentAnalyzer()
        self.excel_writer = excel_writer or ExcelRegistryWriter()

    def process_file(self, file_path, force_reprocess=False):
        path = Path(file_path).resolve()
        stat = path.stat()
        modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
        previous = self.database.find_by_path(path)
        # A full content hash is used for cache validation; mtime/size alone can miss edits.
        sha = self.database.calculate_sha256(path)
        if previous and not force_reprocess and previous.get("sha256") == sha and previous.get("status") == "ok":
            analysis = previous.get("analysis", {})
            return self._record(path, stat.st_size, modified, "ok", "", analysis, cached=True, sha=sha)
        doc = self.document_service.read(path)
        if doc.status != "ok":
            analysis = {}
            status, error = "error", doc.error
        else:
            try:
                analysis = self.analyzer.analyze(doc.text, doc.file_name, metadata=doc.metadata)
                analysis["full_text"] = doc.text
                analysis["metadata"] = doc.metadata
                analysis["attachments"] = doc.attachments
                analysis["extraction_warnings"] = doc.extraction_warnings
                status, error = "ok", ""
            except Exception as exc:
                logger.exception("Ошибка анализа %s", path)
                analysis = {}
                status, error = "error", f"{type(exc).__name__}: {exc}"
        self.database.save_document({
            "file_path":str(path), "file_name":path.name, "file_type":path.suffix.lower().lstrip("."),
            "file_size":stat.st_size, "modified_at":modified, "sha256":sha,
            "status":status, "error":error, "analysis":analysis,
            "full_text": doc.text if doc.status == "ok" else "", "metadata": doc.metadata if doc.status == "ok" else {}
        })
        return self._record(path, stat.st_size, modified, status, error, analysis, cached=False, sha=sha)

    @staticmethod
    def _record(path, size, modified, status, error, analysis, cached, sha):
        return {
            "file_path":str(path), "file_name":path.name, "file_type":path.suffix.lower().lstrip("."),
            "file_size":size, "modified_at":modified, "processed_at":datetime.now(timezone.utc).isoformat(),
            "status":status, "error":error, "cached":cached, "sha256":sha,
            "fields":analysis.get("fields", {}), "matches":analysis.get("matches", []),
            "full_text":analysis.get("full_text", ""), "metadata":analysis.get("metadata", {}),
            "sender":analysis.get("sender", ""), "recipient":analysis.get("recipient", ""), "subject":analysis.get("subject", ""),
            "document_type":analysis.get("document_type", ""), "document_number":analysis.get("document_number", ""),
            "document_date":analysis.get("document_date", ""), "contract_number":analysis.get("contract_number", ""),
            "required_actions":analysis.get("required_actions", []), "deadline":analysis.get("deadline", ""),
            "needs_reply":analysis.get("needs_reply", False), "confidence":analysis.get("confidence", "low"),
            "review_required":analysis.get("review_required", True), "attachments":analysis.get("attachments", []),
            "extraction_warnings":analysis.get("extraction_warnings", []),
            "unmatched_fields":analysis.get("unmatched_fields", []), "summary":analysis.get("summary", ""),
        }

    def process_files(self, file_paths, output_path, progress_callback=None, cancel_event=None, force_reprocess=False):
        records, errors = [], []
        total = len(file_paths)
        cancelled = False
        for index, path in enumerate(file_paths, 1):
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                break
            try:
                record = self.process_file(path, force_reprocess=force_reprocess)
                records.append(record)
                if record["status"] != "ok":
                    errors.append({"file_path":record["file_path"], "error":record["error"]})
            except Exception as exc:
                logger.exception("Не удалось обработать %s", path)
                errors.append({"file_path":str(path), "error":f"{type(exc).__name__}: {exc}"})
            if progress_callback:
                progress_callback(index, total, str(path))
        export_error = ""
        rows_added = 0
        if records:
            try:
                rows_added = self.excel_writer.append_results(output_path, records, True, True)
            except Exception as exc:
                logger.exception("Не удалось экспортировать Excel")
                export_error = f"{type(exc).__name__}: {exc}"
        return {
            "total":total, "processed":len(records), "successful":sum(r["status"]=="ok" for r in records),
            "failed":sum(r["status"]!="ok" for r in records), "skipped":sum(r["cached"] for r in records),
            "cancelled":cancelled, "excel_rows_added":rows_added, "export_error":export_error,
            "errors":errors, "output_path":str(output_path), "records":records,
        }
  
