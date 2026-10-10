from pathlib import Path
from typing import Iterable

# MSG/EML support added in DocuMind 0.2. XLSX remains supported as a source document.
SUPPORTED = {".pdf", ".docx", ".xlsx", ".eml", ".msg"}


def scan_folders(folders, recursive=True, skip_hidden=True) -> Iterable[Path]:
    seen = set()
    for folder in folders:
        base = Path(folder)
        if not base.is_dir():
            continue
        iterator = base.rglob("*") if recursive else base.glob("*")
        for path in iterator:
            try:
                if not path.is_file() or path.suffix.lower() not in SUPPORTED:
                    continue
                resolved = path.resolve()
                if skip_hidden and any(part.startswith(".") for part in resolved.parts):
                    continue
                key = str(resolved).casefold()
                if key not in seen:
                    seen.add(key)
                    yield resolved
            except OSError:
                continue
