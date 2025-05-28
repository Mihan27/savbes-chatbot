# config.py
# Конфигурационный файл для чат-бота САВВЕС

import os

# Yandex API конфигурация
# Исправлен ID папки согласно сообщению об ошибке
YANDEX_API_KEY = os.environ.get('YANDEX_API_KEY', 'YOUR_API_KEY_HERE')
YANDEX_FOLDER_ID = 'b1g0d6n86jgdbi26834g'  # Исправлено с b1g0ddn86jgdb126834g на b1g0d6n86jgdbi26834g

# Конфигурация для отправки email
EMAIL_SENDER = os.environ.get('EMAIL_SENDER', 'your-email@inbox.ru')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'YOUR_PASSWORD_HERE')
EMAIL_RECIPIENT = os.environ.get('EMAIL_RECIPIENT', 'SAVBES@INBOX.RU')
EMAIL_SMTP_SERVER = os.environ.get('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
EMAIL_SMTP_PORT = int(os.environ.get('EMAIL_SMTP_PORT', '587'))

# Флаги функциональности
ENABLE_EMAIL_NOTIFICATIONS = os.environ.get('ENABLE_EMAIL_NOTIFICATIONS', 'False').lower() == 'true'
DEBUG_MODE = os.environ.get('DEBUG_MODE', 'True').lower() == 'true'

# Пути к файлам
SYSTEM_PROMPT_PATH = os.environ.get('SYSTEM_PROMPT_PATH', 'system_prompt.txt')
LOG_FILE_PATH = os.environ.get('LOG_FILE_PATH', 'chat_log.txt')

# Проверка наличия необходимых конфигурационных параметров
if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
    print("Предупреждение: Не указаны YANDEX_API_KEY или YANDEX_FOLDER_ID")

# Настройки для Flask
FLASK_HOST = "0.0.0.0"
FLASK_PORT = int(os.environ.get("PORT", 5000))

# Настройки безопасности
ENABLE_CORS = True  # Включение CORS
USE_YANDEX_GPT = True  # Установите False для отключения YandexGPT и использования только правил