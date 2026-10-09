from pathlib import Path
import os

class ConfigManager:
    def __init__(self):
        # Keep mutable data outside the application folder when possible.
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        self.data_dir = base / "DocuMind"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "logs").mkdir(exist_ok=True)
        self.rules_path = self.data_dir / "rules.json"
        self.database_path = self.data_dir / "documind.sqlite3"
        self.log_path = self.data_dir / "logs" / "documind.log"
