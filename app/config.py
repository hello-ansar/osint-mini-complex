import os

APP_NAME = "Mini-Complex OSINT"
YANDEX_SEARCH_ENABLED = os.getenv("YANDEX_SEARCH_ENABLED", "false").lower() == "true"
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")
USER_SCANNER_BIN = os.getenv("USER_SCANNER_BIN", "user-scanner")
