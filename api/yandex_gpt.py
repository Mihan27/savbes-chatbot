# api/yandex_gpt.py

import logging
import re
import json
import traceback
import os
from typing import Dict, Any, Optional, Union

# Импортируем необходимые модули и классы
try:
    import requests
    from requests.exceptions import RequestException
except ImportError:
    logging.error("Отсутствует библиотека requests. Установите ее с помощью pip install requests")

# Константы для команд запуска калькуляторов
CALCULATOR_COMMANDS = {
    "ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_ОСВЕЩЕНИЕ": "lighting",
    "ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_ЩИТЫ": "panel",
    "ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_РОЗЕТКИ": "socket",
    "ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_КАБЕЛЬ": "cabling",
    "ЗАПУСТИТЬ_КАЛЬКУЛЯТОР": "general"
}

def normalize_api_key(key):
    """Нормализует API-ключ, удаляя невидимые символы и проверяя формат."""
    if not key:
        return ""
    # Удаляем пробелы и невидимые символы
    key = key.strip()
    # Проверяем формат ключа
    if not re.match(r'^[A-Za-z0-9\-_]+$', key):
        logging.warning(f"API-ключ содержит недопустимые символы")
        # Оставляем только допустимые символы
        key = re.sub(r'[^A-Za-z0-9\-_]', '', key)
    return key

def call_yandex_gpt(user_message: str, session_id: str, system_prompt: str = None,
                   chat_history: list = None) -> Dict[str, Any]:
    """
    Отправляет запрос к Yandex GPT API и обрабатывает ответ.

    Args:
        user_message (str): Сообщение пользователя
        session_id (str): Идентификатор сессии
        system_prompt (str, optional): Системный промпт для Yandex GPT
        chat_history (list, optional): История диалога

    Returns:
        Dict[str, Any]: Ответ от API с добавленной информацией о калькуляторе
    """
    logging.info(f"Отправка запроса к Yandex GPT для сессии {session_id}")

    # Логирование диагностической информации о переменных окружения
    logging.info(f"Переменные окружения для Yandex GPT:")
    logging.info(f"YANDEX_GPT_API_KEY: {'Установлен' if os.environ.get('YANDEX_GPT_API_KEY') else 'Не установлен'}")
    logging.info(f"YANDEX_CATALOG_ID: {os.environ.get('YANDEX_CATALOG_ID', 'Не установлен')}")
    logging.info(f"YANDEX_MODEL_NAME: {os.environ.get('YANDEX_MODEL_NAME', 'Не установлен')}")
    logging.info(f"YANDEX_GPT_MODE: {os.environ.get('YANDEX_GPT_MODE', 'Не установлен')}")

    # Подготовка результата на случай ошибок
    default_response = {
        "text": "Извините, я сейчас не могу обработать ваш запрос. Пожалуйста, попробуйте еще раз или свяжитесь с нами по телефону +7(909) 617-97-63.",
        "calculator_type": None,
        "use_multi": False,
        "show_contact_form": False,
        "is_sequential_calculation": False
    }

    try:
        # Проверяем наличие контекста последовательного расчета
        is_sequential_calculation = False
        try:
            from utils.context_manager import get_session_context, is_sequential_calculation_request
            context = get_session_context(session_id)
            if context and context.get("calculation_completed", False) and is_sequential_calculation_request(user_message):
                is_sequential_calculation = True
                logging.info(f"Обнаружен запрос на последовательный расчет для сессии {session_id}")

                # Если это последовательный расчет, загружаем специальный промпт
                system_prompt = create_sequential_calculation_prompt(session_id)
        except ImportError as e:
            logging.warning(f"Не удалось импортировать функции из context_manager: {str(e)}")

        # Получаем настройки из переменных окружения
        API_KEY = normalize_api_key(os.environ.get("YANDEX_GPT_API_KEY", ""))
        CATALOG_ID = os.environ.get("YANDEX_CATALOG_ID", "b1gk3jeds47n0z8i3kdd")
        MODEL_NAME = os.environ.get("YANDEX_MODEL_NAME", "yandexgpt")
        GPT_MODE = os.environ.get("YANDEX_GPT_MODE", "production")

        # Логируем параметры ключа для отладки
        logging.info(f"API_KEY length: {len(API_KEY)}")
        pattern = r'^[A-Za-z0-9\-_]+$'
        logging.info(f"API_KEY format check: {bool(re.match(pattern, API_KEY))}")

        # Если режим тестовый или нет API-ключа, используем тестовый режим
        if GPT_MODE.lower() == "test" or not API_KEY:
            logging.info(f"Используется тестовый режим для сессии {session_id}")
            return get_test_response(user_message, session_id, is_sequential_calculation)

        API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

        headers = {
            "Authorization": "Api-Key " + API_KEY.strip(),
            "Content-Type": "application/json"
        }

        # Создаем сообщения для модели
        messages = []

        # Добавляем системный промпт, если есть
        if system_prompt:
            messages.append({"role": "system", "text": system_prompt})

        # Добавляем историю диалога, если есть
        if chat_history:
            for msg in chat_history:
                # Определяем роль сообщения (user или assistant)
                role = "assistant" if not msg.get("is_user", False) else "user"
                messages.append({"role": role, "text": msg.get("text", "")})

        # Добавляем текущее сообщение пользователя
        messages.append({"role": "user", "text": user_message})

        # Формирование данных для запроса с правильным URI модели
        payload = {
            "modelUri": f"gpt://{CATALOG_ID}/{MODEL_NAME}",
            "completionOptions": {
                "stream": False,
                "temperature": 0.7,
                "maxTokens": 2000
            },
            "messages": messages
        }

        # Расширенное логирование для отладки
        logging.info(f"Отправка запроса к Yandex GPT API с параметрами:")
        logging.info(f"URI модели: {payload['modelUri']}")
        logging.info(f"API URL: {API_URL}")
        logging.info(f"Заголовок Authorization: Api-Key {API_KEY[:5]}...{API_KEY[-5:] if len(API_KEY) > 10 else ''}")
        logging.debug(f"Сообщения для модели: {json.dumps(messages, ensure_ascii=False)[:300]}...")

        try:
            # Отправляем запрос к API
            response = requests.post(
                API_URL,
                headers=headers,
                json=payload,
                timeout=30  # Таймаут 30 секунд
            )

            # Логируем статус ответа
            logging.info(f"Статус ответа от Yandex GPT API: {response.status_code}")
            logging.debug(f"Заголовки ответа: {response.headers}")

            # Если получили ошибку, сначала логируем её, затем проверяем статус
            if response.status_code != 200:
                logging.error(f"Ошибка API: {response.status_code} - {response.text[:500]}")

            response.raise_for_status()  # Проверяем статус ответа

            api_response = response.json()
            logging.info(f"Получен ответ от Yandex GPT API для сессии {session_id}")
            # Логируем структуру ответа для отладки
            logging.debug(f"Структура ответа: {json.dumps(api_response, ensure_ascii=False)[:500]}...")

        except RequestException as e:
            logging.error(f"Ошибка запроса к Yandex GPT API: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Детали ошибки: {e.response.text[:500]}")
            return default_response

        # Извлекаем текст ответа из API-ответа согласно формату ответа Yandex GPT API
        response_text = ""
        if "result" in api_response and "alternatives" in api_response["result"] and len(api_response["result"]["alternatives"]) > 0:
            message = api_response["result"]["alternatives"][0].get("message", {})
            if "text" in message:
                response_text = message["text"]
            else:
                logging.warning(f"Ответ API не содержит текста в message: {message}")
        else:
            logging.warning(f"Необычный формат ответа от API: {api_response}")
            response_text = "Извините, я получил некорректный ответ. Попробуйте задать вопрос иначе."

        # Логируем текст ответа для отладки
        logging.debug(f"Текст ответа: {response_text[:100]}...")

        # Ищем команды запуска калькулятора в ответе
        calculator_type = None
        use_multi = False

        # Проверяем наличие команд запуска калькулятора в ответе
        for command, calc_type in CALCULATOR_COMMANDS.items():
            if command in response_text:
                calculator_type = calc_type
                logging.info(f"Найдена команда {command} в ответе Yandex GPT для сессии {session_id}")
                break

        # Если в ответе не найдена команда калькулятора,
        # но есть упоминания расчета стоимости или цены, пытаемся определить тип калькулятора
        price_keywords = ["стоимость", "цена", "сколько стоит", "рассчитать", "посчитать"]
        if not calculator_type and any(keyword in user_message.lower() for keyword in price_keywords):
            try:
                # Пытаемся определить тип калькулятора на основе сообщения пользователя
                from calculator.calculator_dispatcher import CalculatorDispatcher
                calculator_type, use_multi = CalculatorDispatcher.detect_calculator_type(user_message)
                logging.info(f"Определен тип калькулятора для {session_id} на основе сообщения: {calculator_type}, multi: {use_multi}")
            except Exception as e:
                logging.error(f"Ошибка при определении типа калькулятора: {str(e)}")
                logging.error(traceback.format_exc())
                calculator_type = "general"

        # Проверяем наличие маркера формы контактов
        show_contact_form = "[SHOW_CONTACT_FORM]" in response_text

        # Формируем итоговый ответ
        result = {
            "text": response_text,
            "calculator_type": calculator_type,
            "use_multi": use_multi,
            "show_contact_form": show_contact_form,
            "is_sequential_calculation": is_sequential_calculation
        }

        return result

    except Exception as e:
        logging.error(f"Ошибка при обращении к Yandex GPT API: {str(e)}")
        logging.error(traceback.format_exc())
        return default_response

def get_test_response(user_message: str, session_id: str, is_sequential_calculation: bool = False) -> Dict[str, Any]:
    """
    Генерирует тестовый ответ, когда API не доступно.

    Args:
        user_message (str): Сообщение пользователя
        session_id (str): Идентификатор сессии
        is_sequential_calculation (bool): Флаг последовательного расчета

    Returns:
        Dict[str, Any]: Тестовый ответ
    """
    logging.info(f"Генерация тестового ответа для сессии {session_id}")

    # Определяем тип калькулятора на основе ключевых слов
    calculator_type = None
    use_multi = False
    show_contact_form = False

    user_message_lower = user_message.lower()

    # Проверяем наличие ключевых слов для различных типов услуг
    if any(word in user_message_lower for word in ["свет", "освещение", "светильник", "люстр"]):
        calculator_type = "lighting"
        response_text = "Я могу помочь вам рассчитать стоимость монтажа освещения. ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_ОСВЕЩЕНИЕ"
    elif any(word in user_message_lower for word in ["щит", "автомат", "узо", "электрощит"]):
        calculator_type = "panel"
        response_text = "Давайте рассчитаем стоимость сборки и монтажа электрощита. ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_ЩИТЫ"
    elif any(word in user_message_lower for word in ["розетк", "выключател", "проходной"]):
        calculator_type = "socket"
        response_text = "Я помогу рассчитать стоимость установки розеток и выключателей. ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_РОЗЕТКИ"
    elif any(word in user_message_lower for word in ["кабел", "провод", "линия"]):
        calculator_type = "cabling"
        response_text = "Давайте рассчитаем стоимость кабельных работ. ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_КАБЕЛЬ"
    elif any(word in user_message_lower for word in ["стоимость", "цена", "расчет", "посчитать"]):
        calculator_type = "general"
        response_text = "Я могу помочь рассчитать стоимость электромонтажных работ. ЗАПУСТИТЬ_КАЛЬКУЛЯТОР"
    elif "контакт" in user_message_lower or "телефон" in user_message_lower or "связаться" in user_message_lower:
        response_text = "Для связи с нами, пожалуйста, оставьте свои контактные данные. [SHOW_CONTACT_FORM]"
        show_contact_form = True
    else:
        # Приветствие или общий запрос
        if any(word in user_message_lower for word in ["привет", "здравствуй", "добрый", "здаров"]):
            response_text = "Здравствуйте! Я виртуальный помощник компании САВБЕС. Мы предоставляем услуги электромонтажа в Оренбурге. Чем могу помочь?"
        else:
            response_text = "Я виртуальный помощник компании САВБЕС. Мы предоставляем услуги электромонтажа в Оренбурге. Могу рассказать о наших услугах или помочь рассчитать стоимость работ."
        show_contact_form = False

    # Если это последовательный расчет, адаптируем ответ
    if is_sequential_calculation:
        response_text = "Вы хотите рассчитать еще одну услугу? Давайте посмотрим, что еще мы можем для вас сделать. " + response_text

    return {
        "text": response_text,
        "calculator_type": calculator_type,
        "use_multi": use_multi,
        "show_contact_form": show_contact_form or "контакт" in user_message_lower or "телефон" in user_message_lower,
        "is_sequential_calculation": is_sequential_calculation
    }

def process_yandex_gpt_response(response: Union[Dict[str, Any], str], session_id: str,
                               user_message: str = "") -> Dict[str, Any]:
    """
    Обрабатывает ответ от Yandex GPT API.

    Args:
        response (Union[Dict[str, Any], str]): Ответ от Yandex GPT API
        session_id (str): Идентификатор сессии
        user_message (str, optional): Исходное сообщение пользователя

    Returns:
        Dict[str, Any]: Обработанный ответ
    """
    logging.info(f"Обработка ответа от Yandex GPT для сессии {session_id}")

    try:
        # Преобразуем строку в словарь, если ответ пришел в виде строки
        if isinstance(response, str):
            try:
                response = json.loads(response)
            except json.JSONDecodeError:
                response = {"text": response}

        # Извлекаем текст ответа
        if "text" in response:
            response_text = response["text"]
        elif "result" in response and "alternatives" in response["result"] and len(response["result"]["alternatives"]) > 0:
            response_text = response["result"]["alternatives"][0].get("message", {}).get("text", "")
        elif "alternatives" in response and len(response["alternatives"]) > 0:
            response_text = response["alternatives"][0].get("text", "")
        else:
            response_text = "Извините, я не смог сформировать ответ. Попробуйте переформулировать вопрос."

        # Логируем текст ответа для отладки
        logging.debug(f"Обработанный текст ответа: {response_text[:100]}...")

        # Проверяем наличие команд запуска калькулятора
        calculator_type = None
        use_multi = False

        for command, calc_type in CALCULATOR_COMMANDS.items():
            if command in response_text:
                calculator_type = calc_type
                # Удаляем команду из текста ответа
                response_text = response_text.replace(command, "").strip()
                logging.info(f"Обнаружена команда {command} для запуска калькулятора типа {calc_type}")
                break

        # Если калькулятор не определен из текста ответа,
        # но был определен в исходном ответе, используем его
        if not calculator_type and "calculator_type" in response and response["calculator_type"]:
            calculator_type = response["calculator_type"]
            use_multi = response.get("use_multi", False)
            logging.info(f"Используем определенный ранее тип калькулятора: {calculator_type}, multi: {use_multi}")

        # Проверяем наличие маркера формы контактов
        show_contact_form = "[SHOW_CONTACT_FORM]" in response_text
        if show_contact_form:
            response_text = response_text.replace("[SHOW_CONTACT_FORM]", "").strip()
            logging.info(f"Обнаружен маркер для отображения формы контактов")
        elif "show_contact_form" in response and response["show_contact_form"]:
            show_contact_form = True

        # Проверяем, является ли это последовательным расчетом
        is_sequential_calculation = response.get("is_sequential_calculation", False)

        # Формируем итоговый ответ
        result = {
            "text": response_text,
            "calculator_type": calculator_type,
            "use_multi": use_multi,
            "show_contact_form": show_contact_form,
            "is_sequential_calculation": is_sequential_calculation
        }

        return result

    except Exception as e:
        logging.error(f"Ошибка при обработке ответа от Yandex GPT API: {str(e)}")
        logging.error(traceback.format_exc())

        # В случае ошибки возвращаем простой ответ
        return {
            "text": "Извините, произошла ошибка при обработке ответа. Пожалуйста, попробуйте еще раз.",
            "calculator_type": None,
            "use_multi": False,
            "show_contact_form": False,
            "is_sequential_calculation": False
        }

def detect_calculator_commands_in_text(text: str) -> Optional[str]:
    """
    Определяет команды запуска калькулятора в тексте.

    Args:
        text (str): Текст для анализа

    Returns:
        Optional[str]: Тип калькулятора или None, если команды не найдены
    """
    for command, calc_type in CALCULATOR_COMMANDS.items():
        if command in text:
            return calc_type

    return None

def create_sequential_calculation_prompt(session_id: str) -> str:
    """
    Создает специальный промпт для последовательного расчета.

    Args:
        session_id (str): Идентификатор сессии

    Returns:
        str: Промпт для последовательного расчета
    """
    try:
        from utils.context_manager import get_session_context, get_all_calculation_results

        context = get_session_context(session_id)
        if not context:
            return "# Системный промпт для последовательных расчетов\n\nПользователь хочет рассчитать дополнительные услуги."

        # Получаем предыдущие результаты расчетов
        previous_results = get_all_calculation_results(session_id)
        previous_calculator = context.get("previous_calculator_type", "")

        # Формируем промпт
        prompt = "# Системный промпт для последовательных расчетов\n\n"
        prompt += "Пользователь уже выполнил расчет и теперь хочет рассчитать дополнительную услугу.\n\n"

        if previous_calculator:
            prompt += f"Предыдущий расчет был для: {previous_calculator}\n"

        if previous_results:
            prompt += "\nРанее были рассчитаны:\n"
            for i, result in enumerate(previous_results, 1):
                calc_type = result.get("calculator_type", "общий расчет")
                prompt += f"{i}. {calc_type}\n"

        prompt += "\nОпределите, какую дополнительную услугу хочет рассчитать клиент, и используйте соответствующую команду запуска калькулятора.\n"
        prompt += "Предложите рассчитать услугу и запустите специализированный калькулятор.\n\n"

        # Добавляем инструкции для различных калькуляторов
        prompt += "Доступные команды для запуска калькуляторов:\n"
        prompt += "1. ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_ОСВЕЩЕНИЕ - для расчета монтажа освещения\n"
        prompt += "2. ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_ЩИТЫ - для расчета сборки и монтажа электрощитов\n"
        prompt += "3. ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_РОЗЕТКИ - для расчета установки розеток и выключателей\n"
        prompt += "4. ЗАПУСТИТЬ_КАЛЬКУЛЯТОР_КАБЕЛЬ - для расчета кабельных работ\n"
        prompt += "5. ЗАПУСТИТЬ_КАЛЬКУЛЯТОР - для общего расчета электромонтажных работ\n"

        return prompt
    except ImportError as e:
        logging.warning(f"Не удалось импортировать функции из context_manager: {str(e)}")
        return "# Системный промпт для последовательных расчетов\n\nПользователь хочет рассчитать дополнительные услуги."