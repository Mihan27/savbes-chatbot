# calculator/socket_calculator.py
# Калькулятор для расчета стоимости монтажа розеток и выключателей

import logging
import re
import traceback
from datetime import datetime
from .base_calculator import BaseCalculator, BaseCalculatorDialog
from .services_prices import (
    SOCKET_PRICES,
    COMPLEXITY_COEFFICIENTS,
    WALL_MATERIAL_COEFFICIENTS,
    PROPERTY_TYPE_NAMES,
    SOCKET_TYPE_NAMES,
    get_formatted_name
)

# Создаем отдельный логгер для калькулятора с повышенным уровнем логирования
socket_logger = logging.getLogger('socket_calculator')
socket_logger.setLevel(logging.DEBUG)

class SocketCalculator(BaseCalculator):
    """Калькулятор для расчета стоимости монтажа розеток и выключателей"""
    
    # Переопределяем константы базового класса
    NAME = "Монтаж розеток и выключателей"
    TYPE = "socket"
    
    # Определяем шаги диалога для этого калькулятора
    DIALOG_STEPS = [
        "property_type",
        "wall_material",
        "socket_singles",
        "socket_doubles",
        "socket_power",
        "switch_singles",
        "switch_doubles",
        "other_devices",
        "complexity"
    ]
    
    # Определяем сообщения для каждого шага
    STEP_MESSAGES = {
        "property_type": ("Выберите тип объекта:\n"
                        "1. Квартира\n"
                        "2. Дом/коттедж\n"
                        "3. Офис\n"
                        "4. Коммерческое помещение\n"
                        "5. Промышленное помещение"),
        
        "wall_material": ("Выберите материал стен:\n"
                         "1. Гипсокартон\n"
                         "2. Кирпич\n"
                         "3. Бетон\n"
                         "4. Дерево\n"
                         "5. Газоблок/пеноблок"),
        
        "socket_singles": "Сколько требуется одинарных розеток? (введите число или 0 если не требуются):",
        
        "socket_doubles": "Сколько требуется двойных розеток? (введите число или 0 если не требуются):",
        
        "socket_power": "Сколько требуется силовых розеток? (введите число или 0 если не требуются):",
        
        "switch_singles": "Сколько требуется одноклавишных выключателей? (введите число или 0 если не требуются):",
        
        "switch_doubles": "Сколько требуется двухклавишных выключателей? (введите число или 0 если не требуются):",
        
        "other_devices": ("Выберите дополнительные устройства (можно выбрать несколько, введите номера через запятую):\n"
                         "1. Диммер\n"
                         "2. ТВ розетка\n"
                         "3. Интернет розетка\n"
                         "4. Телефонная розетка\n"
                         "5. USB розетка\n"
                         "0. Не требуются"),
        
        "complexity": ("Выберите сложность монтажа:\n"
                      "1. Простой монтаж (стандартное расположение)\n"
                      "2. Стандартная сложность\n"
                      "3. Сложный монтаж (нестандартное расположение, дополнительные работы)")
    }
    
    # Определяем соответствия для ответов пользователя
    USER_INPUT_MAPPINGS = {
        "property_type": {
            "1": "apartment", "квартира": "apartment",
            "2": "house", "дом": "house", "коттедж": "house",
            "3": "office", "офис": "office",
            "4": "commercial", "коммерческое": "commercial",
            "5": "industrial", "промышленное": "industrial"
        },
        
        "wall_material": {
            "1": "drywall", "гипсокартон": "drywall",
            "2": "brick", "кирпич": "brick",
            "3": "concrete", "бетон": "concrete",
            "4": "wood", "дерево": "wood",
            "5": "block", "газоблок": "block", "пеноблок": "block"
        },
        
        "complexity": {
            "1": "easy", "прост": "easy",
            "2": "standard", "стандарт": "standard",
            "3": "complex", "сложн": "complex"
        }
    }
    
    @classmethod
    def match_user_input(cls, step, user_input):
        """
        Переопределяем метод сопоставления для специфических шагов
        """
        socket_logger.info(f"match_user_input вызван: шаг={step}, ввод='{user_input}'")
        
        try:
            # СПЕЦИАЛЬНАЯ ОБРАБОТКА ДЛЯ OTHER_DEVICES (по образцу lighting_calculator)
            if step == "other_devices":
                socket_logger.info(f"Особая обработка для шага other_devices, ввод='{user_input}'")
                
                # Обрабатываем выбор дополнительных устройств
                device_mapping = {
                    "1": "dimmer",
                    "2": "tv_socket",
                    "3": "network_socket", 
                    "4": "phone_socket",
                    "5": "usb_socket"
                }
                
                selected_devices = {}
                
                # Проверяем на отказ от выбора
                if "0" in user_input or "не треб" in user_input.lower() or "нет" in user_input.lower():
                    socket_logger.info("Пользователь отказался от дополнительных устройств")
                    return {}, True
                
                # Если ввод содержит запятые, разделяем по ним
                if ',' in user_input:
                    socket_logger.info(f"Обнаружен ввод с запятыми: {user_input}")
                    selections = user_input.split(',')
                    for selection in selections:
                        num_match = re.search(r'(\d+)', selection.strip())
                        if num_match:
                            num = num_match.group(1)
                            if num in device_mapping:
                                device_type = device_mapping[num]
                                selected_devices[device_type] = 1
                                socket_logger.info(f"Добавлено устройство {device_type}")
                else:
                    # Проверяем наличие чисел в ответе (для одиночного выбора)
                    numbers = re.findall(r'(\d+)', user_input)
                    for num in numbers:
                        if num in device_mapping:
                            device_type = device_mapping[num]
                            selected_devices[device_type] = 1
                            socket_logger.info(f"Добавлено устройство {device_type}")
                
                socket_logger.info(f"Выбранные устройства: {selected_devices}")
                return selected_devices, True
            
            # СПЕЦИАЛЬНАЯ ОБРАБОТКА ДЛЯ COMPLEXITY (по образцу lighting_calculator)
            if step == "complexity":
                socket_logger.info(f"Особая обработка для шага complexity, ввод='{user_input}'")
                
                complexity_map = {
                    "1": "easy",
                    "2": "standard", 
                    "3": "complex"
                }
                
                # Проверяем прямые совпадения по цифрам
                if user_input.strip() in complexity_map:
                    complexity = complexity_map[user_input.strip()]
                    socket_logger.info(f"Выбрана сложность по цифре: {complexity}")
                    return complexity, True
                
                # Проверяем по ключевым словам
                if "прост" in user_input.lower():
                    return "easy", True
                elif "стандарт" in user_input.lower():
                    return "standard", True
                elif "сложн" in user_input.lower():
                    return "complex", True
                else:
                    socket_logger.info(f"Неизвестная сложность '{user_input}', используем стандартную")
                    return "standard", True
            
            # Используем стандартное сопоставление для шагов с маппингами
            if step in cls.USER_INPUT_MAPPINGS:
                mappings = cls.USER_INPUT_MAPPINGS[step]
                
                # Проверяем прямые совпадения
                for key, value in mappings.items():
                    if key in user_input.lower():
                        socket_logger.info(f"Найдено совпадение для {step}: {key} -> {value}")
                        return value, True
                
                # Если нет совпадений, но ввод - это просто число
                if user_input.isdigit() and user_input in mappings:
                    socket_logger.info(f"Найдено числовое совпадение для {step}: {user_input} -> {mappings[user_input]}")
                    return mappings[user_input], True
                
                socket_logger.warning(f"Нет совпадений для {step}, ввод='{user_input}'")
                return None, False
            
            # Для шагов с количеством устройств
            if step in ["socket_singles", "socket_doubles", "socket_power", "switch_singles", "switch_doubles"]:
                try:
                    count_match = re.search(r'(\d+)', user_input)
                    if count_match:
                        count = int(count_match.group(1))
                        socket_logger.info(f"Распознано количество для {step}: {count}")
                        return count, True
                    elif "нет" in user_input.lower() or "не" in user_input.lower() or "0" in user_input:
                        socket_logger.info(f"Распознано 'нет' для {step}, возвращаем 0")
                        return 0, True
                    else:
                        socket_logger.warning(f"Не удалось распознать количество для {step}")
                        return None, False
                except Exception as e:
                    socket_logger.error(f"Ошибка при обработке количества: {str(e)}")
                    return None, False
            
            # Для неизвестных шагов возвращаем ввод пользователя как есть
            socket_logger.info(f"Неизвестный шаг {step}, возвращаем ввод как есть")
            return user_input, True
            
        except Exception as e:
            socket_logger.error(f"Ошибка в match_user_input для {step}: {str(e)}")
            socket_logger.error(traceback.format_exc())
            
            # Возвращаем значения по умолчанию
            if step == "property_type":
                return "apartment", True
            elif step == "wall_material":
                return "brick", True
            elif step == "complexity":
                return "standard", True
            elif step in ["socket_singles", "socket_doubles", "socket_power", "switch_singles", "switch_doubles"]:
                return 0, True
            elif step == "other_devices":
                return {}, True
            else:
                return user_input, True
    
    def calculate(self, data):
        """
        Рассчитывает стоимость монтажа розеток и выключателей
        """
        socket_logger.info(f"Запуск calculate с данными: {data}")
        
        try:
            # Установка значений по умолчанию для обязательных параметров
            property_type = data.get("property_type", "apartment")
            wall_material = data.get("wall_material", "brick")
            complexity = data.get("complexity", "standard")
            
            # Конвертация чисел с безопасными значениями по умолчанию
            def safe_int(value, default=0):
                try:
                    return int(value)
                except (ValueError, TypeError):
                    socket_logger.warning(f"Не удалось преобразовать {value} в целое число, используем {default}")
                    return default
            
            socket_singles = safe_int(data.get("socket_singles", 0))
            socket_doubles = safe_int(data.get("socket_doubles", 0))
            socket_power = safe_int(data.get("socket_power", 0))
            switch_singles = safe_int(data.get("switch_singles", 0))
            switch_doubles = safe_int(data.get("switch_doubles", 0))
            
            # Безопасное получение словаря дополнительных устройств
            other_devices = {}
            if "other_devices" in data:
                if isinstance(data["other_devices"], dict):
                    other_devices = data["other_devices"]
                else:
                    socket_logger.warning(f"other_devices имеет неверный тип {type(data['other_devices'])}, используем пустой словарь")
            
            # Проверка на корректные значения
            if property_type not in PROPERTY_TYPE_NAMES:
                socket_logger.warning(f"Неизвестный тип объекта: {property_type}, используем 'apartment'")
                property_type = "apartment"
                
            if wall_material not in WALL_MATERIAL_COEFFICIENTS:
                socket_logger.warning(f"Неизвестный материал стен: {wall_material}, используем 'brick'")
                wall_material = "brick"
                
            if complexity not in COMPLEXITY_COEFFICIENTS:
                socket_logger.warning(f"Неизвестная сложность: {complexity}, используем 'standard'")
                complexity = "standard"
            
            # Получаем коэффициенты
            complexity_coefficient = COMPLEXITY_COEFFICIENTS.get(complexity, 1.0)
            wall_coefficient = WALL_MATERIAL_COEFFICIENTS.get(wall_material, 1.0)
            
            # Словарь устройств для расчета
            devices = {
                "socket_single": socket_singles,
                "socket_double": socket_doubles,
                "socket_power": socket_power,
                "switch_single": switch_singles,
                "switch_double": switch_doubles
            }
            
            # Добавляем дополнительные устройства
            devices.update(other_devices)
            
            # Рассчитываем стоимость каждого типа устройства
            device_prices = {}
            total_price = 0
            
            for device_type, count in devices.items():
                if count > 0:
                    price_per_unit = SOCKET_PRICES.get(device_type, 350)  # Базовая цена 350 руб.
                    device_total = price_per_unit * count
                    
                    device_prices[device_type] = {
                        "count": count,
                        "price_per_unit": price_per_unit,
                        "total_price": device_total
                    }
                    
                    total_price += device_total
            
            # Применяем коэффициенты
            total_price_with_coefficients = total_price * complexity_coefficient * wall_coefficient
            
            # Минимальная стоимость заказа
            min_order_price = 2000
            if total_price_with_coefficients < min_order_price:
                total_price_with_coefficients = min_order_price
            
            # Считаем общее количество устройств
            devices_total = sum(count for count in devices.values() if count > 0)
            
            # Формируем результат
            result = {
                "property_type": property_type,
                "wall_material": wall_material,
                "complexity": complexity,
                "devices": devices,
                "device_prices": device_prices,
                "devices_total": devices_total,
                "total_price": round(total_price_with_coefficients),
                "price": round(total_price_with_coefficients)  # Для совместимости с другими калькуляторами
            }
            
            socket_logger.info(f"Расчет успешно завершен, результат: {result}")
            return result
            
        except Exception as e:
            socket_logger.error(f"Ошибка при расчете: {str(e)}")
            socket_logger.error(traceback.format_exc())
            
            # Возвращаем базовый результат в случае ошибки
            return {
                "property_type": data.get("property_type", "apartment"),
                "wall_material": data.get("wall_material", "brick"),
                "complexity": "standard",
                "devices_total": 0,
                "total_price": 0,
                "price": 0
            }
    
    def format_result(self, calculation):
        """
        Форматирует результат расчета в читаемый текст
        """
        socket_logger.info("Запуск format_result")
        
        try:
            # Получаем удобочитаемые названия для кодов
            property_type = get_formatted_name(PROPERTY_TYPE_NAMES, calculation.get('property_type', 'apartment'))
            wall_material = get_formatted_name(WALL_MATERIAL_COEFFICIENTS, calculation.get('wall_material', 'brick'))
            complexity = get_formatted_name(COMPLEXITY_COEFFICIENTS, calculation.get('complexity', 'standard'))
            
            # Форматируем текст результата
            result = "🔌 Расчет стоимости монтажа розеток и выключателей:\n\n"
            
            # Основные параметры
            result += f"• Тип объекта: {property_type}\n"
            result += f"• Материал стен: {wall_material}\n"
            result += f"• Сложность монтажа: {complexity}\n\n"
            
            # Устройства
            result += "Устройства:\n"
            
            device_prices = calculation.get("device_prices", {})
            
            # Названия устройств для отображения
            device_names = {
                "socket_single": "розетка одинарная",
                "socket_double": "розетка двойная", 
                "socket_power": "розетка силовая",
                "switch_single": "выключатель одноклавишный",
                "switch_double": "выключатель двухклавишный",
                "dimmer": "диммер",
                "tv_socket": "ТВ розетка",
                "network_socket": "интернет розетка",
                "phone_socket": "телефонная розетка",
                "usb_socket": "USB розетка"
            }
            
            for device_type, price_info in device_prices.items():
                device_name = device_names.get(device_type, device_type)
                count = price_info["count"]
                price_per_unit = price_info["price_per_unit"]
                total_price = price_info["total_price"]
                
                result += f"• {device_name}: {count} шт. x {price_per_unit} руб. = {total_price} руб.\n"
            
            # Общая информация
            devices_total = calculation.get("devices_total", 0)
            result += f"\nВсего устройств: {devices_total} шт. 💡\n"
            
            # Итоговая стоимость
            result += f"\n💰 Общая стоимость монтажа: {calculation.get('total_price', 0)} руб.\n"
            
            # Добавляем важное примечание
            result += "\n⚠️ ВНИМАНИЕ: Это предварительная оценка стоимости монтажа розеток и выключателей. "
            result += "Точная стоимость определяется после выезда специалиста на объект и уточнения деталей заказа. "
            result += "Цена может измениться в зависимости от сложности работ и других особенностей объекта."
            
            socket_logger.info("format_result успешно завершен")
            return result
        
        except Exception as e:
            socket_logger.error(f"Ошибка в format_result: {str(e)}")
            socket_logger.error(traceback.format_exc())
            
            # В случае ошибки возвращаем простой результат
            return f"Результат расчета: {calculation.get('total_price', 0)} руб.\n\nПожалуйста, обратитесь к менеджеру для получения детальной информации."


# Функции для интеграции с диспетчером калькуляторов

def start_socket_calculation(session_id, chat_states, initial_data=None):
    """
    Запускает калькулятор монтажа розеток и выключателей
    """
    socket_logger.info(f"Запуск калькулятора розеток для сессии {session_id}")
    try:
        return BaseCalculatorDialog.start_dialog(SocketCalculator, session_id, chat_states, initial_data)
    except Exception as e:
        socket_logger.error(f"Ошибка при запуске калькулятора: {str(e)}")
        socket_logger.error(traceback.format_exc())
        return "К сожалению, произошла ошибка при запуске калькулятора. Пожалуйста, попробуйте еще раз или обратитесь к менеджеру."

def process_socket_calculation(user_input, session_id, chat_states):
    """
    Обрабатывает ввод пользователя в диалоге калькулятора розеток и выключателей
    ПО ОБРАЗЦУ process_lighting_calculation
    """
    socket_logger.info(f"Обработка ввода '{user_input}' для сессии {session_id}")
    
    try:
        # ✅ ИСПРАВЛЕНО: Импортируем BaseCalculatorDialog в начале функции
        from calculator.base_calculator import BaseCalculatorDialog
        
        # Если нужно отменить расчет
        if user_input.lower() in ["отмена", "стоп", "прервать", "отменить"]:
            if session_id in chat_states:
                del chat_states[session_id]
            socket_logger.info(f"Расчет отменен для сессии {session_id}")
            return "Расчет стоимости отменен. Чем еще я могу вам помочь?"
        
        # СПЕЦИАЛЬНАЯ ОБРАБОТКА ДЛЯ ЭТАПА COLLECT_CONTACT (обработка контактных данных)
        if (session_id in chat_states and 
            chat_states[session_id].get("stage") == "collect_contact"):
            
            socket_logger.info(f"Обнаружен этап сбора контактных данных для сессии {session_id}")
            
            # Пытаемся извлечь телефон
            phone_match = re.search(r'(\+7|8)?[\s\-]?\(?(\d{3})\)?[\s\-]?(\d{3})[\s\-]?(\d{2})[\s\-]?(\d{2})', user_input)
            phone = phone_match.group(0) if phone_match else None
            
            # Пытаемся извлечь email
            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', user_input)
            email = email_match.group(0) if email_match else None
            
            # Остальное считаем именем (упрощенный подход)
            name = user_input
            if phone:
                name = name.replace(phone, '').strip()
            if email:
                name = name.replace(email, '').strip()
            name = name.strip(',').strip()
            
            if phone:
                socket_logger.info(f"Извлечены контактные данные: имя={name}, телефон={phone}, email={email}")
                
                # Сохраняем контактные данные
                chat_states[session_id]["contact_data"] = {
                    "name": name,
                    "phone": phone,
                    "email": email
                }
                
                # Получаем результат расчета
                calculation_result = chat_states[session_id].get("calculation_result", "")
                full_calc = chat_states[session_id].get("full_calc", {})
                
                # Отправляем заявку на email
                try:
                    from utils import email_sender
                    # Импортируем chat_history из app
                    try:
                        from app import chat_history
                    except ImportError:
                        chat_history = {}
                    
                    if email_sender:
                        dialog_history = []
                        if session_id in chat_history:
                            dialog_history = chat_history[session_id]
                        
                        success = email_sender.send_client_request(
                            phone_number=phone,
                            dialog_history=dialog_history,
                            calculation_results=full_calc,
                            name=name,
                            email=email
                        )
                        
                        if success:
                            socket_logger.info("Заявка успешно отправлена")
                        else:
                            socket_logger.error("Ошибка при отправке заявки")
                except Exception as e:
                    socket_logger.error(f"Ошибка при отправке email: {str(e)}")
                
                # ВАЖНО: Удаляем состояние калькулятора, чтобы завершить диалог
                del chat_states[session_id]
                
                # Возвращаем благодарность
                return (f"Спасибо! Ваша заявка принята. Наш специалист свяжется с вами по телефону {phone} "
                       "в ближайшее время для уточнения деталей и согласования времени выезда.\n\n"
                       "Чем еще я могу вам помочь?")
            else:
                # Если не удалось извлечь телефон, просим ввести снова
                return "Пожалуйста, укажите номер телефона для связи. Например: +7 922 825 8279"
        
        # СПЕЦИАЛЬНАЯ ОБРАБОТКА ДЛЯ ШАГА OTHER_DEVICES с запятыми
        if (session_id in chat_states and 
            chat_states[session_id].get("stage") == "other_devices" and 
            (',' in user_input or user_input.strip() in ["1", "2", "3", "4", "5", "0"])):
            
            socket_logger.info(f"Обнаружен выбор дополнительных устройств: '{user_input}'")
            
            device_mapping = {
                "1": "dimmer",
                "2": "tv_socket",
                "3": "network_socket", 
                "4": "phone_socket",
                "5": "usb_socket"
            }
            
            device_names = {
                "dimmer": "Диммер",
                "tv_socket": "ТВ розетка",
                "network_socket": "Интернет розетка",
                "phone_socket": "Телефонная розетка",
                "usb_socket": "USB розетка"
            }
            
            selected_devices = {}
            
            # Проверяем на отказ от выбора
            if "0" in user_input or "не треб" in user_input.lower() or "нет" in user_input.lower():
                selected_devices = {}
            else:
                # Если ввод содержит запятые, разделяем по ним
                if ',' in user_input:
                    selections = user_input.split(',')
                    for selection in selections:
                        num_match = re.search(r'(\d+)', selection.strip())
                        if num_match:
                            num = num_match.group(1)
                            if num in device_mapping:
                                device_type = device_mapping[num]
                                selected_devices[device_type] = 1
                else:
                    # Проверяем наличие чисел в ответе (для одиночного выбора)
                    numbers = re.findall(r'(\d+)', user_input)
                    for num in numbers:
                        if num in device_mapping:
                            device_type = device_mapping[num]
                            selected_devices[device_type] = 1
            
            # Корректная обработка: используем BaseCalculatorDialog.process_dialog
            # который правильно обработает текущий шаг
            result = BaseCalculatorDialog.process_dialog(SocketCalculator, user_input, session_id, chat_states)
            
            # Но добавляем информацию о выбранных устройствах к результату
            if selected_devices:
                device_list = [device_names.get(dev, dev) for dev in selected_devices.keys()]
                selected_text = f"Выбраны дополнительные устройства: {', '.join(device_list)}\n\n"
                return selected_text + result
            else:
                selected_text = "Дополнительные устройства не выбраны.\n\n"
                return selected_text + result
        
        # СПЕЦИАЛЬНАЯ ОБРАБОТКА ДЛЯ ШАГА COMPLEXITY (по образцу lighting_calculator)
        if (session_id in chat_states and 
            chat_states[session_id].get("stage") == "complexity" and 
            user_input.strip() in ["1", "2", "3"]):
            
            socket_logger.info(f"Обнаружен выбор сложности: '{user_input}'")
            
            complexity_map = {
                "1": "easy",
                "2": "standard",
                "3": "complex"
            }
            complexity_text_map = {
                "1": "Простой монтаж",
                "2": "Стандартная сложность",
                "3": "Сложный монтаж"
            }
            
            # Устанавливаем выбранную сложность
            complexity = complexity_map.get(user_input.strip(), "standard")
            chat_states[session_id]["data"]["complexity"] = complexity
            
            # Сохраняем текстовое значение выбора для отображения
            chat_states[session_id]["complexity_answer"] = complexity_text_map.get(user_input.strip(), "Стандартная сложность")
            
            # ✅ ИСПРАВЛЕНО: Отмечаем этап как сбор контактов, а НЕ завершенный
            chat_states[session_id]["stage"] = "collect_contact"
            
            # Производим расчет
            calculator = SocketCalculator()
            calculation = calculator.calculate(chat_states[session_id]["data"])
            result = calculator.format_result(calculation)
            
            # Сохраняем результат
            chat_states[session_id]["calculation_result"] = result
            chat_states[session_id]["full_calc"] = calculation
            
            # Возвращаем результат с запросом контактных данных
            contact_request = "\n\nХотите получить точный расчет и консультацию специалиста? Пожалуйста, оставьте свои контактные данные (имя, телефон, email), и наш мастер свяжется с вами в ближайшее время.[SHOW_CONTACT_FORM]"
            return result + contact_request
        
        # Стандартная обработка
        return BaseCalculatorDialog.process_dialog(SocketCalculator, user_input, session_id, chat_states)
        
    except Exception as e:
        socket_logger.error(f"Ошибка при обработке ввода: {str(e)}")
        socket_logger.error(traceback.format_exc())
        
        # Сбрасываем состояние в случае критической ошибки
        if session_id in chat_states:
            del chat_states[session_id]
            
        return "К сожалению, произошла ошибка при обработке вашего запроса. Пожалуйста, начните расчет заново или обратитесь к менеджеру по телефону +7(909) 617-97-63."