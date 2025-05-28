# utils/email_sender.py
# Модуль для отправки email с историей диалога и контактами клиента

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from datetime import datetime
import os
import traceback
import ssl

# Получаем конфигурацию из переменных окружения или используем значения по умолчанию
EMAIL_SENDER = os.environ.get('EMAIL_SENDER', 'savbes@inbox.ru')  # Ваш email на Mail.ru
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'xejF6ZaBNXBLybg9V5hj')  # Пароль от почты
EMAIL_RECIPIENT = os.environ.get('EMAIL_RECIPIENT', 'savbes@inbox.ru')  # Куда отправлять результаты
EMAIL_SMTP_SERVER = os.environ.get('EMAIL_SMTP_SERVER', 'smtp.pythonanywhere.com')  # SMTP-сервер PythonAnywhere
EMAIL_SMTP_PORT = int(os.environ.get('EMAIL_SMTP_PORT', '587'))  # Порт для STARTTLS
ENABLE_EMAIL_NOTIFICATIONS = os.environ.get('ENABLE_EMAIL_NOTIFICATIONS', 'True').lower() == 'true'

# Настройка дополнительного логирования для отладки email
EMAIL_DEBUG_LOG = 'email_debug.log'
email_logger = logging.getLogger('email_sender')
email_logger.setLevel(logging.DEBUG)

# Настройка файлового логирования
try:
    file_handler = logging.FileHandler(EMAIL_DEBUG_LOG)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    email_logger.addHandler(file_handler)
except Exception as e:
    logging.warning(f"Could not setup email debug log file: {str(e)}")

def send_email(subject, body, attachments=None):
    """
    Отправляет email с заданной темой и текстом
    
    Args:
        subject (str): Тема письма
        body (str): Текст письма
        attachments (list, optional): Список файлов для прикрепления
        
    Returns:
        bool: True если письмо успешно отправлено, иначе False
    """
    # Логирование начала отправки
    logging.info(f"Attempting to send email: {subject}")
    logging.info(f"Email settings: SERVER={EMAIL_SMTP_SERVER}, PORT={EMAIL_SMTP_PORT}, SENDER={EMAIL_SENDER}, RECIPIENT={EMAIL_RECIPIENT}")
    
    if not ENABLE_EMAIL_NOTIFICATIONS:
        logging.info("Email notifications disabled in config")
        return False
    
    # Проверяем наличие реального получателя
    recipient = EMAIL_RECIPIENT or 'savbes@inbox.ru'
    
    # Проверяем настройки
    if not EMAIL_SMTP_SERVER or not EMAIL_SENDER or not EMAIL_PASSWORD:
        logging.warning(f"Missing email configuration. Would send to {recipient}: {subject}")
        logging.debug(f"Email body: {body[:500]}...")  # Логируем начало тела письма
        return False
    
    try:
        logging.info("Creating email message")
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = recipient
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Добавление вложений, если они есть
        if attachments:
            for attachment in attachments:
                logging.debug(f"Attaching file: {attachment}")
                with open(attachment, "rb") as file:
                    part = MIMEText(file.read())
                    part.add_header('Content-Disposition', f'attachment; filename="{attachment}"')
                    msg.attach(part)
        
        logging.info(f"Creating SSL context for connection to {EMAIL_SMTP_SERVER}:{EMAIL_SMTP_PORT}")
        
        # Создаем контекст SSL
        context = ssl.create_default_context()
        
        # Подключение к SMTP-серверу с учетом порта
        logging.info(f"Using {'SSL' if EMAIL_SMTP_PORT == 465 else 'STARTTLS'} connection")
        
        if EMAIL_SMTP_PORT == 465:
            # Используем SSL для порта 465
            logging.info(f"Establishing SSL connection to {EMAIL_SMTP_SERVER}:{EMAIL_SMTP_PORT}")
            server = smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, context=context)
        else:
            # Используем STARTTLS для других портов (например, 587)
            logging.info(f"Establishing STARTTLS connection to {EMAIL_SMTP_SERVER}:{EMAIL_SMTP_PORT}")
            server = smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT)
            server.starttls(context=context)
        
        # Включаем подробное логирование SMTP
        server.set_debuglevel(1)
        
        logging.info(f"Logging in as {EMAIL_SENDER}")
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        logging.info(f"Successfully logged in as {EMAIL_SENDER}")
        
        logging.info(f"Sending email to {recipient}")
        server.sendmail(EMAIL_SENDER, recipient, msg.as_string())
        logging.info("Email sent successfully")
        
        logging.info("Closing connection")
        server.quit()
        
        logging.info(f"Email process completed for: {subject}")
        return True
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        logging.error(f"Error sending email: {str(e)}")
        logging.error(f"Traceback: {error_traceback}")
        
        # Для отладки логируем, что пытались отправить
        logging.info(f"Email would be sent to {recipient}: {subject}")
        logging.info(f"Email body: {body[:500]}...")  # Логируем начало тела письма
        return False

def format_property_type(code):
    """Преобразует код типа объекта в читаемое название"""
    property_types = {
        "apartment": "Квартира",
        "house": "Дом/коттедж",
        "office": "Офис",
        "commercial": "Коммерческое помещение",
        "industrial": "Промышленное помещение"
    }
    return property_types.get(code, code)

def format_wall_material(code):
    """Преобразует код материала стен в читаемое название"""
    materials = {
        "drywall": "Гипсокартон",
        "brick": "Кирпич",
        "concrete": "Бетон",
        "wood": "Дерево",
        "block": "Газоблок/пеноблок"
    }
    return materials.get(code, code)

def format_additional_services(services):
    """Преобразует коды дополнительных услуг в читаемые названия"""
    service_names = {
        "security_system": "Система безопасности",
        "video_surveillance": "Видеонаблюдение",
        "generator_connection": "Подключение генератора"
    }
    return [service_names.get(s, s) for s in services]

def send_client_request(phone_number, dialog_history, calculation_results=None, name=None, email=None):
    """
    Отправляет заявку клиента на email с историей диалога
    
    Args:
        phone_number (str): Номер телефона клиента
        dialog_history (list): История диалога
        calculation_results (dict, optional): Результаты расчета
        name (str, optional): Имя клиента
        email (str, optional): Email клиента
        
    Returns:
        bool: True если письмо успешно отправлено, иначе False
    """
    logging.info(f"Sending client request for phone: {phone_number}")
    
    # Формируем тему письма
    subject = f"Новая заявка с сайта САВБЕС - Номер телефона: {phone_number}"
    
    # Форматируем историю диалога
    dialog_text = ""
    if dialog_history:
        dialog_entries = []
        for msg in dialog_history:
            timestamp = msg.get('timestamp', '')
            if timestamp:
                try:
                    time_str = datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    time_str = timestamp
            else:
                time_str = ''
            
            role = 'Клиент' if msg.get('is_user', False) else 'Бот'
            text = msg.get('text', '')
            dialog_entries.append(f"{time_str} {role}: {text}")
        
        dialog_text = "\n".join(dialog_entries)
    
    # Форматируем результаты расчета, если они есть
    calculation_text = ""
    if calculation_results:
        calculation_text = "\n\nРезультаты расчета:\n"
        
        # Добавляем основную информацию
        if "total_price" in calculation_results:
            calculation_text += f"• Общая стоимость: {calculation_results['total_price']} руб.\n"
        elif "price" in calculation_results:
            calculation_text += f"• Общая стоимость: {calculation_results['price']} руб.\n"
        
        # Добавляем детальную информацию
        if "property_type" in calculation_results:
            property_type = format_property_type(calculation_results["property_type"])
            calculation_text += f"• Тип объекта: {property_type}\n"
        
        if "area" in calculation_results:
            calculation_text += f"• Площадь: {calculation_results['area']} кв.м\n"
        
        if "rooms" in calculation_results or "num_rooms" in calculation_results:
            rooms = calculation_results.get("rooms", calculation_results.get("num_rooms", 0))
            calculation_text += f"• Количество комнат/помещений: {rooms}\n"
        
        if "wall_material" in calculation_results:
            wall_material = format_wall_material(calculation_results["wall_material"])
            calculation_text += f"• Материал стен: {wall_material}\n"
        
        if "additional_services" in calculation_results and calculation_results["additional_services"]:
            services = format_additional_services(calculation_results["additional_services"])
            calculation_text += f"• Дополнительные услуги: {', '.join(services)}\n"
        
        if "points" in calculation_results:
            calculation_text += f"• Количество точек: {calculation_results['points']}\n"
    
    # Форматируем текст письма
    client_info = f"Номер телефона: {phone_number}\n"
    if name:
        client_info += f"Имя: {name}\n"
    if email:
        client_info += f"Email: {email}\n"
        
    body = f"""
Новая заявка с сайта САВБЕС!

{client_info}
Время заявки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{calculation_text}

История диалога:
{dialog_text}
    """
    
    # Отправляем письмо
    return send_email(subject, body)

def send_daily_report(dialog_count, request_count, calculation_count):
    """
    Отправляет ежедневный отчет о работе бота
    
    Args:
        dialog_count (int): Количество диалогов за день
        request_count (int): Количество заявок за день
        calculation_count (int): Количество расчетов за день
        
    Returns:
        bool: True если письмо успешно отправлено, иначе False
    """
    today = datetime.now().strftime('%Y-%m-%d')
    subject = f"Отчет о работе чат-бота САВБЕС за {today}"
    
    # Расчет конверсии с проверкой деления на ноль
    dialog_conversion = 0
    if dialog_count > 0:
        dialog_conversion = round(request_count / dialog_count * 100, 2)
    
    calc_conversion = 0
    if calculation_count > 0:
        calc_conversion = round(request_count / calculation_count * 100, 2)
    
    body = f"""
Отчет о работе чат-бота САВБЕС за {today}

1. Общее количество диалогов: {dialog_count}
2. Количество полученных заявок: {request_count}
3. Количество выполненных расчетов: {calculation_count}
4. Конверсия диалогов в заявки: {dialog_conversion}%
5. Конверсия расчетов в заявки: {calc_conversion}%

Это автоматический отчет, сгенерированный системой.
    """
    
    return send_email(subject, body)

def test_email_connection():
    """
    Тестирует подключение к SMTP серверу и отправку тестового письма
    
    Returns:
        dict: Словарь с результатами теста
    """
    results = {
        "smtp_server": EMAIL_SMTP_SERVER,
        "smtp_port": EMAIL_SMTP_PORT,
        "sender": EMAIL_SENDER,
        "recipient": EMAIL_RECIPIENT,
        "password_set": bool(EMAIL_PASSWORD),
        "steps": []
    }
    
    try:
        results["steps"].append({"step": "Initializing connection", "status": "started"})
        
        context = ssl.create_default_context()
        results["steps"].append({"step": "Creating SSL context", "status": "success"})
        
        if EMAIL_SMTP_PORT == 465:
            # Используем SSL для порта 465
            server = smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, context=context)
            results["steps"].append({"step": "Creating SSL connection", "status": "success"})
        else:
            # Используем STARTTLS для других портов (например, 587)
            server = smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT)
            results["steps"].append({"step": "Creating SMTP connection", "status": "success"})
            server.starttls(context=context)
            results["steps"].append({"step": "Upgrading to STARTTLS", "status": "success"})
        
        server.set_debuglevel(1)
        results["steps"].append({"step": "Setting debug level", "status": "success"})
        
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        results["steps"].append({"step": "Authentication", "status": "success"})
        
        msg = MIMEText("This is a test email from САВБЕС bot")
        msg['Subject'] = 'САВБЕС Bot - Test Email'
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        
        server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
        results["steps"].append({"step": "Sending email", "status": "success"})
        
        server.quit()
        results["steps"].append({"step": "Closing connection", "status": "success"})
        results["overall_result"] = "success"
        
    except Exception as e:
        results["steps"].append({"step": "Error", "status": "failed", "error": str(e)})
        results["overall_result"] = "failed"
        results["traceback"] = traceback.format_exc()
    
    return results