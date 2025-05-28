from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import logging
import traceback
import os
import random
import string
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

# ✅ CORS поддержка
CORS(app, origins=["https://www.savbes.ru", "https://savbes.ru", "http://localhost:3000"])

# Глобальные переменные для хранения состояний
chat_states = {}
chat_history = {}
DIALOG_HISTORY = chat_history  # Алиас для совместимости с base_calculator.py

# Импорты модулей
try:
    from calculator import calculator_dispatcher
    logging.info("Calculator dispatcher успешно импортирован")
except ImportError as e:
    logging.error(f"Ошибка импорта calculator_dispatcher: {str(e)}")
    calculator_dispatcher = None

try:
    from api import yandex_gpt
    logging.info("Yandex GPT API успешно импортирован")
except ImportError as e:
    logging.error(f"Ошибка импорта yandex_gpt: {str(e)}")
    yandex_gpt = None

try:
    from utils import email_sender
    logging.info("Email sender успешно импортирован")
except ImportError as e:
    logging.error(f"Ошибка импорта email_sender: {str(e)}")
    email_sender = None


def save_message_to_context(session_id, message, is_user=True):
    """
    Сохраняет сообщение в контекст сессии
    """
    try:
        # Инициализируем глобальные словари если их нет
        global chat_history, chat_states

        if chat_history is None:
            chat_history = {}
        if chat_states is None:
            chat_states = {}

        # Инициализируем контекст сессии если его нет
        if session_id not in chat_history:
            chat_history[session_id] = []
            logging.info(f"Создан новый контекст для сессии {session_id}")

        # Создаем запись сообщения
        message_record = {
            'text': str(message),  # Приводим к строке для безопасности
            'is_user': bool(is_user),
            'timestamp': datetime.now().isoformat()
        }

        # Добавляем в историю
        chat_history[session_id].append(message_record)

        # Ограничиваем размер истории (последние 50 сообщений)
        if len(chat_history[session_id]) > 50:
            chat_history[session_id] = chat_history[session_id][-50:]
            logging.info(f"Обрезана история для сессии {session_id} до 50 сообщений")

        logging.info(f"Сообщение сохранено в контекст для сессии {session_id}")
        return True

    except Exception as e:
        logging.error(f"Ошибка сохранения сообщения в контекст для сессии {session_id}: {str(e)}")
        logging.error(f"Детали ошибки: {traceback.format_exc()}")
        return False


def load_system_prompt():
    """
    Загружает системный промпт из файла
    """
    try:
        with open('system_prompt.txt', 'r', encoding='utf-8') as file:
            prompt = file.read()
            logging.info(f"Загружен системный промпт длиной {len(prompt)} символов")
            return prompt
    except Exception as e:
        logging.error(f"Ошибка загрузки системного промпта: {str(e)}")
        return None


def detect_calculation_intent(message):
    """
    Определяет намерение пользователя на расчет услуг
    """
    message_lower = message.lower()
    
    # ❌ ИСКЛЮЧЕНИЯ - НЕ считать расчетом
    exclusion_phrases = [
        'какие есть услуги', 'что за услуги', 'какие услуги', 'перечень услуг',
        'список услуг', 'виды услуг', 'ваши услуги', 'услуги компании',
        'какие работы', 'что делаете', 'чем занимаетесь'
    ]
    
    for exclusion in exclusion_phrases:
        if exclusion in message_lower:
            logging.info(f"Исключение: НЕ расчет по фразе: {exclusion}")
            return False
    
    # ✅ ТОЧНЫЕ фразы расчета (высокий приоритет)
    calculation_phrases = [
        'расчет стоимости', 'рассчитать стоимость', 'сколько стоит', 
        'калькулятор', 'цена за', 'стоимость работ', 'во сколько обойдется',
        'посчитайте стоимость', 'хочу рассчитать', 'нужен расчет'
    ]
    
    for phrase in calculation_phrases:
        if phrase in message_lower:
            logging.info(f"Обнаружен интент расчета по точной фразе: {phrase}")
            return True
    
    # ✅ Специальная обработка для комплексных запросов
    multi_service_phrases = [
        'несколько услуг', 'комплекс услуг', 'разные услуги',
        'много услуг', 'все услуги', 'комплексный',
        'мне надо несколько', 'нужно несколько', 'хочу несколько'
    ]

    for phrase in multi_service_phrases:
        if phrase in message_lower:
            logging.info(f"Обнаружен интент комплексного расчета по фразе: {phrase}")
            return True

    # ✅ КОНКРЕТНЫЕ потребности (только с указанием конкретных работ)
    specific_needs = [
        'нужны розетки', 'нужно освещение', 'нужен щит', 'нужна проводка',
        'установить розетки', 'поставить выключатели', 'подключить светильники',
        'монтаж розеток', 'монтаж освещения', 'монтаж щита',
        'проложить кабель', 'провести проводку'
    ]
    
    for need in specific_needs:
        if need in message_lower:
            logging.info(f"Обнаружен интент расчета по конкретной потребности: {need}")
            return True

    return False


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    # ✅ Обработка preflight запроса
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Отсутствуют данные'}), 400

        message = data.get('message', '').strip()
        session_id = data.get('session_id', '')

        if not message:
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400

        if not session_id:
            # Генерируем новый session_id если не передан
            session_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
            logging.info(f"Сгенерирован новый session_id: {session_id}")

        logging.info(f"Обработка запроса от сессии {session_id}: {message}")

        # Сохраняем сообщение пользователя
        if not save_message_to_context(session_id, message, is_user=True):
            logging.warning(f"Could not save message to context for session {session_id}")

        # Инициализируем chat_states если нужно
        global chat_states
        if chat_states is None:
            chat_states = {}

        # 🔧 ИСПРАВЛЕНО: Проверяем, есть ли активный диалог с калькулятором
        if session_id in chat_states:
            logging.info(f"Продолжение активного диалога для сессии {session_id}")

            # Получаем тип активного калькулятора
            calculator_type = chat_states[session_id].get("calculator_type", "socket")
            
            # 🎯 ПРАВИЛЬНО: Используем dispatcher для обработки активного диалога
            try:
                response = calculator_dispatcher.CalculatorDispatcher.process_calculation(
                    calculator_type, message, session_id, chat_states
                )
            except Exception as e:
                logging.error(f"Ошибка при обработке активного диалога: {str(e)}")
                logging.error(f"Traceback: {traceback.format_exc()}")
                response = "Произошла ошибка. Начните диалог заново."
                chat_states.pop(session_id, None)

        else:
            # Новый диалог - определяем интент
            if detect_calculation_intent(message):
                logging.info(f"Обнаружен интент расчета для сессии {session_id}")

                if calculator_dispatcher:
                    try:
                        # Используем обновленный dispatcher для извлечения деталей
                        calculator_type, use_multi, extracted_params = calculator_dispatcher.CalculatorDispatcher.detect_calculator_details(message)

                        # 🎯 ПРАВИЛЬНО: Запускаем соответствующий калькулятор через dispatcher
                        response = calculator_dispatcher.CalculatorDispatcher.start_calculation(
                            calculator_type, session_id, chat_states, extracted_params
                        )
                    except Exception as e:
                        logging.error(f"Ошибка в calculator_dispatcher: {str(e)}")
                        logging.error(f"Traceback: {traceback.format_exc()}")
                        response = "Произошла ошибка при запуске калькулятора. Попробуйте еще раз."
                else:
                    response = "Калькулятор временно недоступен. Попробуйте позже."

            else:
                # Обычный диалог - используем Yandex GPT
                logging.info(f"Обычный диалог для сессии {session_id}")

                if yandex_gpt:
                    try:
                        # Получаем историю чата для передачи в API
                        chat_history_for_api = chat_history.get(session_id, [])

                        # Загружаем системный промпт
                        system_prompt = load_system_prompt()

                        # Вызываем Yandex GPT API
                        api_response = yandex_gpt.call_yandex_gpt(
                            message,
                            session_id,
                            system_prompt=system_prompt,
                            chat_history=chat_history_for_api
                        )

                        # ✅ ГЛАВНОЕ ИСПРАВЛЕНИЕ: Правильная обработка ответа от API
                        if isinstance(api_response, dict):
                            # Если ответ - словарь, извлекаем текст
                            response = api_response.get('text', api_response.get('response', 'Произошла ошибка при получении ответа'))
                            
                            # 🔧 ИСПРАВЛЕНИЕ: Проверяем команды калькулятора в тексте ответа
                            calculator_commands = {
                                'ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_РОЗЕТКИ': 'socket',
                                'ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_ОСВЕЩЕНИЯ': 'lighting',
                                'ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_ЩИТОВ': 'panel',
                                'ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_КАБЕЛЕЙ': 'cabling',
                                'ЗАПУСТИТЬ_МНОГОФУНКЦИОНАЛЬНЫЙ_КАЛЬКУЛЯТОР': 'multi'
                            }
                            
                            detected_calculator = None
                            for command, calc_type in calculator_commands.items():
                                if command in response:
                                    detected_calculator = calc_type
                                    # Убираем команду из ответа
                                    response = response.replace(command, "").strip()
                                    logging.info(f"Обнаружена команда калькулятора: {command} -> {calc_type}")
                                    break
                            
                            # Проверяем, есть ли команды калькулятора в ответе (старый способ)
                            calculator_type = api_response.get('calculator_type') or detected_calculator
                            
                            if calculator_type and calculator_dispatcher:
                                try:
                                    logging.info(f"Запуск калькулятора {calculator_type} из GPT ответа")
                                    # Извлекаем параметры и запускаем калькулятор
                                    extracted_calculator_type, use_multi, extracted_params = calculator_dispatcher.CalculatorDispatcher.detect_calculator_details(message)
                                    calc_response = calculator_dispatcher.CalculatorDispatcher.start_calculation(
                                        calculator_type, session_id, chat_states, extracted_params
                                    )
                                    # Заменяем ответ на ответ калькулятора
                                    response = calc_response
                                    logging.info(f"Калькулятор успешно запущен")
                                except Exception as e:
                                    logging.error(f"Ошибка запуска калькулятора из GPT ответа: {str(e)}")
                                    logging.error(f"Traceback: {traceback.format_exc()}")
                                    response = "Произошла ошибка при запуске калькулятора. Попробуйте еще раз."
                                    
                        elif isinstance(api_response, str):
                            # Если ответ - строка, используем как есть
                            response = api_response
                        else:
                            # Если что-то другое, приводим к строке
                            response = str(api_response)
                            logging.warning(f"Неожиданный тип ответа от Yandex GPT: {type(api_response)}")

                        # Проверяем, не пустой ли ответ
                        if not response or len(response.strip()) == 0:
                            response = "Извините, не смог сформировать ответ. Попробуйте переформулировать вопрос."

                    except Exception as e:
                        logging.error(f"Ошибка при вызове Yandex GPT: {str(e)}")
                        logging.error(f"Traceback: {traceback.format_exc()}")
                        response = "Извините, произошла ошибка. Попробуйте позже или обратитесь к нашим специалистам."
                else:
                    response = "Извините, сервис временно недоступен. Обратитесь к нашим специалистам для получения консультации."

        # Сохраняем ответ бота
        if not save_message_to_context(session_id, response, is_user=False):
            logging.warning(f"Could not save bot response to context for session {session_id}")

        return jsonify({
            'response': response,
            'session_id': session_id
        })

    except Exception as e:
        logging.error(f"Произошла ошибка при обработке запроса: {str(e)}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/contact', methods=['POST', 'OPTIONS'])
def contact():
    """
    Обрабатывает отправку контактных данных
    """
    # ✅ Обработка preflight запроса
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Отсутствуют данные'}), 400

        phone = data.get('phone', '').strip()
        name = data.get('name', '').strip()
        email_addr = data.get('email', '').strip()
        session_id = data.get('session_id', '')

        if not phone:
            return jsonify({'error': 'Номер телефона обязателен'}), 400

        logging.info(f"Получены контактные данные: {name}, {phone}, {email_addr}")

        # Получаем историю диалога и результаты расчета
        dialog_history = chat_history.get(session_id, [])
        calculation_results = None

        if session_id in chat_states:
            calculation_results = chat_states[session_id].get("full_calc")

        # Отправляем заявку на email если есть email_sender
        if email_sender:
            try:
                success = email_sender.send_client_request(
                    phone_number=phone,
                    dialog_history=dialog_history,
                    calculation_results=calculation_results,
                    name=name,
                    email=email_addr
                )

                if success:
                    logging.info(f"Заявка успешно отправлена для {phone}")
                    return jsonify({'success': True, 'message': 'Заявка отправлена!'})
                else:
                    logging.error(f"Ошибка отправки заявки для {phone}")
                    return jsonify({'success': False, 'message': 'Ошибка отправки заявки'})
            except Exception as e:
                logging.error(f"Исключение при отправке email: {str(e)}")
                return jsonify({'success': False, 'message': 'Ошибка отправки заявки'})
        else:
            logging.info(f"Email sender недоступен, данные сохранены: {phone}")
            return jsonify({'success': True, 'message': 'Данные сохранены!'})

    except Exception as e:
        logging.error(f"Ошибка при обработке контактных данных: {str(e)}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)