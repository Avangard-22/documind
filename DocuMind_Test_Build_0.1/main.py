from app.config_manager import ConfigManager
from app.interface import DocuMindWindow

def main():
    config = ConfigManager()
    app = DocuMindWindow(config)
    app.run()

if __name__ == "__main__":
    main()
