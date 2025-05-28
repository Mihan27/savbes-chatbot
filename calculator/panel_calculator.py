# calculator/panel_calculator.py
# Калькулятор для расчета стоимости монтажа электрощита

import logging
import re
import traceback
from datetime import datetime
from .base_calculator import BaseCalculator, BaseCalculatorDialog
from .services_prices import (
    PANEL_BASE_RATES,
    PANEL_DEVICE_PRICES,
    COMPLEXITY_COEFFICIENTS,
    WALL_MATERIAL_COEFFICIENTS,
    PROPERTY_TYPE_NAMES,
    PANEL_TYPE_NAMES, 
    DEVICE_TYPE_NAMES,
    get_formatted_name
)

# Создаем отдельный логгер для калькулятора с повышенным уровнем логирования
panel_logger = logging.getLogger('panel_calculator')
panel_logger.setLevel(logging.DEBUG)

class PanelCalculator(BaseCalculator):
    """Калькулятор для расчета стоимости монтажа электрощита"""
    
    # Переопределяем константы базового класса
    NAME = "Монтаж электрощита"
    TYPE = "panel"
    
    # Определяем шаги диалога для этого калькулятора
    DIALOG_STEPS = [
        "property_type",
        "wall_material",
        "panel_type",
        "circuit_breakers",
        "rcd_count",
        "diff_auto_count",
        "meter_installation",
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
        
        "panel_type": ("Выберите тип электрощита:\n"
                      "1. Квартирный щиток\n"
                      "2. Щит для частного дома\n"
                      "3. Этажный щит\n"
                      "4. Промышленный щит"),
        
        "circuit_breakers": "Укажите количество обычных автоматов (однополюсных и двухполюсных), которые необходимо установить:",
        
        "rcd_count": "Укажите количество УЗО (устройств защитного отключения), которые необходимо установить (или 0, если не требуется):",
        
        "diff_auto_count": "Укажите количество дифавтоматов, которые необходимо установить (или 0, если не требуется):",
        
        "meter_installation": "Требуется ли установка электросчетчика? (Да/Нет)",
        
        "other_devices": ("Выберите дополнительные устройства (можно выбрать несколько, введите номера через запятую):\n"
                         "1. Контактор\n"
                         "2. Реле напряжения\n"
                         "3. Таймер\n"
                         "4. Устройство контроля фаз\n"
                         "0. Не требуются"),
        
        "complexity": ("Выберите сложность монтажа:\n"
                      "1. Простой монтаж (стандартное расположение)\n"
                      "2. Стандартная сложность\n"
                      "3. Сложный монтаж (нестандартное расположение, дополнительные работы)\n"
                      "4. Очень сложный монтаж (промышленное исполнение, сложное программирование)")
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
        
        "panel_type": {
            "1": "apartment", "квартирн": "apartment",
            "2": "house", "частн": "house", "дом": "house",
            "3": "floor", "этаж": "floor",
            "4": "industrial", "промышл": "industrial"
        },
        
        "meter_installation": {
            "да": True, "yes": True, "1": True, "нужно": True, "требу": True,
            "нет": False, "no": False, "0": False, "не": False
        },
        
        "complexity": {
            "1": "easy", "прост": "easy",
            "2": "standard", "стандарт": "standard",
            "3": "complex", "сложн": "complex",
            "4": "very_complex", "очень сложн": "very_complex"
        }
    }
    
    @classmethod
    def match_user_input(cls, step, user_input):
        """
        Переопределяем метод сопоставления для специфических шагов
        """
        panel_logger.info(f"match_user_input вызван: шаг={step}, ввод='{user_input}'")
        
        try:
            # СПЕЦИАЛЬНАЯ ОБРАБОТКА ДЛЯ COMPLEXITY
            if step == "complexity":
                panel_logger.info(f"Особая обработка для шага complexity, ввод='{user_input}'")
                
                # Маппинг выбора сложности на текстовые значения
                complexity_map = {
                    "1": "easy",
                    "2": "standard", 
                    "3": "complex",
                    "4": "very_complex"
                }
                
                # Проверяем прямые совпадения по цифрам
                if user_input.strip() in complexity_map:
                    complexity = complexity_map[user_input.strip()]
                    panel_logger.info(f"Выбрана сложность по цифре: {complexity}")
                    return complexity, True
                
                # Проверяем по ключевым словам
                if "прост" in user_input.lower():
                    panel_logger.info("Выбрана простая сложность (easy)")
                    return "easy", True
                elif "стандарт" in user_input.lower():
                    panel_logger.info("Выбрана стандартная сложность (standard)")
                    return "standard", True
                elif "очень сложн" in user_input.lower() or "очень" in user_input.lower():
                    panel_logger.info("Выбрана очень сложная сложность (very_complex)")
                    return "very_complex", True
                elif "сложн" in user_input.lower():
                    panel_logger.info("Выбрана сложная сложность (complex)")
                    return "complex", True
                else:
                    # По умолчанию стандартная сложность
                    panel_logger.info(f"Неизвестная сложность '{user_input}', используем стандартную")
                    return "standard", True
                    
            # Обработка установки счетчика
            elif step == "meter_installation":
                panel_logger.info(f"Обработка установки счетчика, ввод='{user_input}'")
                
                user_input_lower = user_input.lower()
                if any(word in user_input_lower for word in ["да", "yes", "нужно", "требу", "установить"]):
                    panel_logger.info("Выбрана установка счетчика")
                    return True, True
                elif any(word in user_input_lower for word in ["нет", "no", "не нужно", "не требу"]):
                    panel_logger.info("Отказ от установки счетчика")
                    return False, True
                else:
                    # По умолчанию не устанавливаем
                    panel_logger.info(f"Неясный ответ об установке счетчика '{user_input}', считаем что не нужно")
                    return False, True
                    
            # Используем стандартное сопоставление для шагов с маппингами
            if step in cls.USER_INPUT_MAPPINGS:
                mappings = cls.USER_INPUT_MAPPINGS[step]
                
                # Проверяем прямые совпадения
                for key, value in mappings.items():
                    if key in user_input.lower():
                        panel_logger.info(f"Найдено совпадение для {step}: {key} -> {value}")
                        return value, True
                
                # Если нет совпадений, но ввод - это просто число
                if user_input.isdigit() and user_input in mappings:
                    panel_logger.info(f"Найдено числовое совпадение для {step}: {user_input} -> {mappings[user_input]}")
                    return mappings[user_input], True
                
                panel_logger.warning(f"Нет совпадений для {step}, ввод='{user_input}'")
                return None, False
            
            # Для шагов с количеством устройств
            if step in ["circuit_breakers", "rcd_count", "diff_auto_count"]:
                # Парсим количество устройств
                try:
                    count = int(re.search(r'(\d+)', user_input).group(1))
                    if count < 0:
                        panel_logger.warning(f"Отрицательное количество для {step}: {count}")
                        return None, False
                    panel_logger.info(f"Распознано количество для {step}: {count}")
                    return count, True
                except:
                    # Если число не найдено, проверяем на "нет" и т.п.
                    if "нет" in user_input.lower() or "не" in user_input.lower() or "0" in user_input:
                        panel_logger.info(f"Распознано 'нет' для {step}, возвращаем 0")
                        return 0, True
                    panel_logger.warning(f"Не удалось распознать количество для {step}, ввод='{user_input}'")
                    return None, False
            
            # Особая обработка для дополнительных устройств
            elif step == "other_devices":
                panel_logger.info(f"Обработка дополнительных устройств, ввод='{user_input}'")
                
                # Обрабатываем выбор дополнительных устройств
                device_mapping = {
                    "1": "contactor",
                    "2": "voltage_relay",
                    "3": "timer",
                    "4": "phase_control"
                }
                
                selected_devices = {}
                
                # Проверяем на отказ от выбора
                if "0" in user_input or "не треб" in user_input.lower() or "нет" in user_input.lower():
                    # Пользователь выбрал "Не требуются"
                    panel_logger.info("Пользователь отказался от дополнительных устройств")
                    return {}, True
                
                # Если ввод содержит запятые, разделяем по ним
                if ',' in user_input:
                    panel_logger.info(f"Обнаружен ввод с запятыми: {user_input}")
                    # Разбиваем ввод по запятым
                    selections = user_input.split(',')
                    for selection in selections:
                        # Ищем число в каждой части
                        num_match = re.search(r'(\d+)', selection.strip())
                        if num_match:
                            num = num_match.group(1)
                            if num in device_mapping:
                                device_type = device_mapping[num]
                                
                                # Всегда используем количество 1 для упрощения
                                qty = 1
                                
                                selected_devices[device_type] = qty
                                panel_logger.info(f"Добавлено устройство {device_type} в количестве {qty} шт.")
                else:
                    # Проверяем наличие чисел в ответе (для одиночного выбора)
                    numbers = re.findall(r'(\d+)', user_input)
                    
                    for num in numbers:
                        if num in device_mapping:
                            device_type = device_mapping[num]
                            qty = 1  # По умолчанию 1 устройство
                            selected_devices[device_type] = qty
                            panel_logger.info(f"Добавлено устройство {device_type} в количестве {qty} шт.")
                
                panel_logger.info(f"Выбраны устройства: {selected_devices}")
                return selected_devices, True
            
            # Для неизвестных шагов возвращаем ввод пользователя как есть
            panel_logger.info(f"Неизвестный шаг {step}, возвращаем ввод как есть")
            return user_input, True
            
        except Exception as e:
            # Перехватываем все ошибки для надежности
            panel_logger.error(f"Ошибка в match_user_input для {step}: {str(e)}")
            panel_logger.error(traceback.format_exc())
            
            # Возвращаем значения по умолчанию
            if step == "property_type":
                return "apartment", True
            elif step == "wall_material":
                return "brick", True
            elif step == "panel_type":
                return "apartment", True
            elif step == "complexity":
                return "standard", True
            elif step == "meter_installation":
                return False, True
            elif step in ["circuit_breakers", "rcd_count", "diff_auto_count"]:
                return 0, True
            elif step == "other_devices":
                return {}, True
            else:
                return user_input, True
    
    def calculate(self, data):
        """
        Рассчитывает стоимость монтажа электрощита
        """
        panel_logger.info(f"Запуск calculate с данными: {data}")
        
        try:
            # Установка значений по умолчанию для обязательных параметров
            property_type = data.get("property_type", "apartment")
            wall_material = data.get("wall_material", "brick")
            panel_type = data.get("panel_type", "apartment")
            complexity = data.get("complexity", "standard")
            
            # Конвертация чисел с безопасными значениями по умолчанию
            def safe_int(value, default=0):
                try:
                    return int(value)
                except (ValueError, TypeError):
                    panel_logger.warning(f"Не удалось преобразовать {value} в целое число, используем {default}")
                    return default
            
            circuit_breakers = safe_int(data.get("circuit_breakers", 0))
            rcd_count = safe_int(data.get("rcd_count", 0))
            diff_auto_count = safe_int(data.get("diff_auto_count", 0))
            meter_installation = bool(data.get("meter_installation", False))
            
            # Безопасное получение словаря дополнительных устройств
            other_devices = {}
            if "other_devices" in data:
                if isinstance(data["other_devices"], dict):
                    other_devices = data["other_devices"]
                else:
                    panel_logger.warning(f"other_devices имеет неверный тип {type(data['other_devices'])}, используем пустой словарь")
            
            # Проверка на корректные значения
            if panel_type not in PANEL_TYPE_NAMES:
                panel_logger.warning(f"Неизвестный тип щита: {panel_type}, используем 'apartment'")
                panel_type = "apartment"
                
            if property_type not in PROPERTY_TYPE_NAMES:
                panel_logger.warning(f"Неизвестный тип объекта: {property_type}, используем 'apartment'")
                property_type = "apartment"
                
            if wall_material not in WALL_MATERIAL_COEFFICIENTS:
                panel_logger.warning(f"Неизвестный материал стен: {wall_material}, используем 'brick'")
                wall_material = "brick"
                
            if complexity not in COMPLEXITY_COEFFICIENTS:
                panel_logger.warning(f"Неизвестная сложность: {complexity}, используем 'standard'")
                complexity = "standard"
            
            # Получаем базовую стоимость щита
            base_price = PANEL_BASE_RATES.get(panel_type, PANEL_BASE_RATES.get("apartment", 5000))
            
            # Получаем коэффициенты
            complexity_coefficient = COMPLEXITY_COEFFICIENTS.get(complexity, 1.0)
            wall_coefficient = WALL_MATERIAL_COEFFICIENTS.get(wall_material, 1.0)
            
            # Рассчитываем стоимость автоматов
            circuit_breaker_price = PANEL_DEVICE_PRICES.get("circuit_breaker_1p", 350) * circuit_breakers
            
            # Стоимость УЗО
            rcd_price = PANEL_DEVICE_PRICES.get("rcd_2p", 500) * rcd_count
            
            # Стоимость дифавтоматов
            diff_auto_price = PANEL_DEVICE_PRICES.get("diff_auto", 800) * diff_auto_count
            
            # Стоимость установки счетчика
            meter_price = PANEL_DEVICE_PRICES.get("counter", 1500) if meter_installation else 0
            
            # Стоимость прочих устройств
            other_devices_price = 0
            device_prices = {}
            
            for device_type, count in other_devices.items():
                price_per_unit = PANEL_DEVICE_PRICES.get(device_type, 0)
                device_price = price_per_unit * count
                other_devices_price += device_price
                
                device_prices[device_type] = {
                    "count": count,
                    "price_per_unit": price_per_unit,
                    "total_price": device_price
                }
            
            # Суммарная базовая стоимость
            subtotal = base_price + circuit_breaker_price + rcd_price + diff_auto_price + meter_price + other_devices_price
            
            # Применяем коэффициенты
            total_price = subtotal * complexity_coefficient * wall_coefficient
            
            # Минимальная стоимость заказа
            min_order_price = 5000
            if total_price < min_order_price:
                total_price = min_order_price
            
            # Считаем общее количество устройств
            total_devices = circuit_breakers + rcd_count + diff_auto_count + sum(other_devices.values()) + (1 if meter_installation else 0)
            
            # Формируем результат
            result = {
                "property_type": property_type,
                "wall_material": wall_material,
                "panel_type": panel_type,
                "complexity": complexity,
                "circuit_breakers": circuit_breakers,
                "rcd_count": rcd_count,
                "diff_auto_count": diff_auto_count,
                "meter_installation": meter_installation,
                "other_devices": other_devices,
                "device_prices": device_prices,
                "base_price": base_price,
                "total_devices": total_devices,
                "total_price": round(total_price),
                "price": round(total_price)  # Для совместимости с другими калькуляторами
            }
            
            panel_logger.info(f"Расчет успешно завершен, результат: {result}")
            return result
            
        except Exception as e:
            panel_logger.error(f"Ошибка при расчете: {str(e)}")
            panel_logger.error(traceback.format_exc())
            
            # Возвращаем базовый результат в случае ошибки
            return {
                "property_type": data.get("property_type", "apartment"),
                "wall_material": data.get("wall_material", "brick"),
                "panel_type": data.get("panel_type", "apartment"),
                "complexity": "standard",
                "total_devices": 0,
                "total_price": 0,
                "price": 0
            }
    
    def format_result(self, calculation):
        """
        Форматирует результат расчета в читаемый текст
        """
        panel_logger.info("Запуск format_result")
        
        try:
            # Получаем удобочитаемые названия для кодов
            property_type = get_formatted_name(PROPERTY_TYPE_NAMES, calculation.get('property_type', 'apartment'))
            wall_material = get_formatted_name(WALL_MATERIAL_COEFFICIENTS, calculation.get('wall_material', 'brick'))
            panel_type = get_formatted_name(PANEL_TYPE_NAMES, calculation.get('panel_type', 'apartment'))
            complexity = get_formatted_name(COMPLEXITY_COEFFICIENTS, calculation.get('complexity', 'standard'))
            
            # Форматируем текст результата
            result = "⚡ Расчет стоимости монтажа электрощита:\n\n"
            
            # Основные параметры
            result += f"• Тип объекта: {property_type}\n"
            result += f"• Материал стен: {wall_material}\n"
            result += f"• Тип щита: {panel_type}\n"
            result += f"• Сложность монтажа: {complexity}\n\n"
            
            # Устройства
            result += "Устройства:\n"
            
            if calculation.get("circuit_breakers", 0) > 0:
                result += f"• Автоматы: {calculation['circuit_breakers']} шт.\n"
            
            if calculation.get("rcd_count", 0) > 0:
                result += f"• УЗО: {calculation['rcd_count']} шт.\n"
            
            if calculation.get("diff_auto_count", 0) > 0:
                result += f"• Дифавтоматы: {calculation['diff_auto_count']} шт.\n"
            
            if calculation.get("meter_installation", False):
                result += f"• Установка счетчика: Да\n"
            
            # Дополнительные устройства
            other_devices = calculation.get("other_devices", {})
            if other_devices:
                result += "• Дополнительные устройства:\n"
                for device_type, count in other_devices.items():
                    device_name = get_formatted_name(DEVICE_TYPE_NAMES, device_type)
                    result += f"  - {device_name}: {count} шт.\n"
            
            # Итоговая стоимость
            result += f"\n💰 Общая стоимость монтажа: {calculation.get('total_price', 0)} руб.\n"
            
            # Добавляем важное примечание
            result += "\n⚠️ ВНИМАНИЕ: Это предварительная оценка стоимости монтажа электрощита. "
            result += "Точная стоимость определяется после выезда специалиста на объект и уточнения деталей заказа. "
            result += "Цена может измениться в зависимости от сложности работ и других особенностей объекта."
            
            panel_logger.info("format_result успешно завершен")
            return result
        
        except Exception as e:
            panel_logger.error(f"Ошибка в format_result: {str(e)}")
            panel_logger.error(traceback.format_exc())
            
            # В случае ошибки возвращаем простой результат
            return f"Результат расчета: {calculation.get('total_price', 0)} руб.\n\nПожалуйста, обратитесь к менеджеру для получения детальной информации."


# Функции для интеграции с диспетчером калькуляторов

def start_panel_calculation(session_id, chat_states, initial_data=None):
    """
    Запускает калькулятор монтажа электрощита
    
    Args:
        session_id (str): Идентификатор сессии
        chat_states (dict): Словарь состояний чата
        initial_data (dict, optional): Начальные данные
        
    Returns:
        str: Первое сообщение калькулятора (ВСЕГДА строка)
    """
    panel_logger.info(f"Запуск калькулятора электрощита для сессии {session_id}")
    try:
        result = BaseCalculatorDialog.start_dialog(PanelCalculator, session_id, chat_states, initial_data)
        
        # ИСПРАВЛЕНО: Убеждаемся что возвращаем строку
        if isinstance(result, dict):
            result_text = result.get("text", result.get("response", str(result)))
            panel_logger.warning(f"BaseCalculatorDialog.start_dialog вернул dict вместо строки: {result}")
            return result_text
        else:
            return str(result)  # Принудительно конвертируем в строку
            
    except Exception as e:
        panel_logger.error(f"Ошибка при запуске калькулятора: {str(e)}")
        panel_logger.error(traceback.format_exc())
        return "К сожалению, произошла ошибка при запуске калькулятора. Пожалуйста, попробуйте еще раз или обратитесь к менеджеру."

def process_panel_calculation(user_input, session_id, chat_states):
    """
    Обрабатывает ввод пользователя в диалоге калькулятора электрощита
    
    Args:
        user_input (str): Сообщение пользователя
        session_id (str): Идентификатор сессии
        chat_states (dict): Словарь состояний чата
        
    Returns:
        str: Ответ калькулятора (ВСЕГДА строка)
    """
    panel_logger.info(f"Обработка ввода '{user_input}' для сессии {session_id}")
    
    try:
        # Если нужно отменить расчет
        if user_input.lower() in ["отмена", "стоп", "прервать", "отменить"]:
            if session_id in chat_states:
                del chat_states[session_id]
            panel_logger.info(f"Расчет отменен для сессии {session_id}")
            return "Расчет стоимости отменен. Чем еще я могу вам помочь?"
        
        # ИСПРАВЛЕНО: Используем только BaseCalculatorDialog.process_dialog без дополнительной обработки
        result = BaseCalculatorDialog.process_dialog(PanelCalculator, user_input, session_id, chat_states)
        
        # ИСПРАВЛЕНО: Убеждаемся что возвращаем строку
        if isinstance(result, dict):
            result_text = result.get("text", result.get("response", str(result)))
            panel_logger.warning(f"BaseCalculatorDialog.process_dialog вернул dict вместо строки: {result}")
            return result_text
        else:
            return str(result)  # Принудительно конвертируем в строку
        
    except Exception as e:
        panel_logger.error(f"Ошибка при обработке ввода: {str(e)}")
        panel_logger.error(traceback.format_exc())
        
        # Сбрасываем состояние в случае критической ошибки
        if session_id in chat_states:
            del chat_states[session_id]
            
        return "К сожалению, произошла ошибка при обработке вашего запроса. Пожалуйста, начните расчет заново или обратитесь к менеджеру по телефону +7(909) 617-97-63."