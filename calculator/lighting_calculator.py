# calculator/lighting_calculator.py
# Калькулятор стоимости монтажа освещения

import logging
import re
import traceback
from datetime import datetime
from .base_calculator import BaseCalculator, BaseCalculatorDialog
from .services_prices import (
    LIGHTING_PRICES, COMPLEXITY_COEFFICIENTS, WALL_MATERIAL_COEFFICIENTS,
    PROPERTY_TYPE_NAMES, WALL_MATERIAL_NAMES, COMPLEXITY_LEVEL_NAMES, 
    get_formatted_name
)

# Создаем отдельный логгер для калькулятора с повышенным уровнем логирования
lighting_logger = logging.getLogger('lighting_calculator')
lighting_logger.setLevel(logging.DEBUG)

class LightingCalculator(BaseCalculator):
    """Калькулятор для расчета стоимости монтажа освещения"""
    
    # Переопределяем константы базового класса
    NAME = "Монтаж освещения"
    TYPE = "lighting"
    
    # Определяем шаги диалога для этого калькулятора
    DIALOG_STEPS = [
        "property_type",
        "wall_material",
        "ceiling_height",
        "ceiling_type",
        "light_fixtures",
        "chandelier",
        "spot_lights",
        "wall_lights",
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
        
        "ceiling_height": "Укажите высоту потолков в метрах:",
        
        "ceiling_type": ("Выберите тип потолка:\n"
                        "1. Обычный (бетонная плита)\n"
                        "2. Гипсокартонный\n"
                        "3. Натяжной\n"
                        "4. Подвесной (Армстронг и т.п.)"),
        
        "light_fixtures": "Сколько всего светильников нужно установить?",
        
        "chandelier": "Сколько люстр или подвесных светильников нужно установить? (введите число или 0 если не требуются):",
        
        "spot_lights": "Сколько точечных светильников нужно установить? (введите число или 0 если не требуются):",
        
        "wall_lights": "Сколько настенных светильников нужно установить? (введите число или 0 если не требуются):",
        
        "complexity": ("Выберите сложность монтажа:\n"
                      "1. Простой монтаж (стандартное расположение)\n"
                      "2. Стандартная сложность\n"
                      "3. Сложный монтаж (нестандартное расположение)\n"
                      "4. Очень сложный монтаж (фигурные потолки, сложная схема подключения)")
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
        
        "ceiling_type": {
            "1": "regular", "обычный": "regular", "бетон": "regular",
            "2": "drywall", "гипсокартон": "drywall",
            "3": "stretch", "натяжной": "stretch",
            "4": "suspended", "подвесной": "suspended", "армстронг": "suspended"
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
        lighting_logger.info(f"match_user_input вызван: шаг={step}, ввод='{user_input}'")
        
        try:
            # СПЕЦИАЛЬНАЯ ОБРАБОТКА ДЛЯ COMPLEXITY
            if step == "complexity":
                lighting_logger.info(f"Особая обработка для шага complexity, ввод='{user_input}'")
                
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
                    lighting_logger.info(f"Выбрана сложность по цифре: {complexity}")
                    return complexity, True
                
                # Проверяем по ключевым словам
                if "прост" in user_input.lower():
                    lighting_logger.info("Выбрана простая сложность (easy)")
                    return "easy", True
                elif "стандарт" in user_input.lower():
                    lighting_logger.info("Выбрана стандартная сложность (standard)")
                    return "standard", True
                elif "очень сложн" in user_input.lower() or "очень" in user_input.lower():
                    lighting_logger.info("Выбрана очень сложная сложность (very_complex)")
                    return "very_complex", True
                elif "сложн" in user_input.lower():
                    lighting_logger.info("Выбрана сложная сложность (complex)")
                    return "complex", True
                else:
                    # По умолчанию стандартная сложность
                    lighting_logger.info(f"Неизвестная сложность '{user_input}', используем стандартную")
                    return "standard", True
                    
            # Используем стандартное сопоставление для шагов с маппингами
            if step in cls.USER_INPUT_MAPPINGS:
                mappings = cls.USER_INPUT_MAPPINGS[step]
                
                # Проверяем прямые совпадения
                for key, value in mappings.items():
                    if key in user_input.lower():
                        lighting_logger.info(f"Найдено совпадение для {step}: {key} -> {value}")
                        return value, True
                
                # Если нет совпадений, но ввод - это просто число
                if user_input.isdigit() and user_input in mappings:
                    lighting_logger.info(f"Найдено числовое совпадение для {step}: {user_input} -> {mappings[user_input]}")
                    return mappings[user_input], True
                
                lighting_logger.warning(f"Нет совпадений для {step}, ввод='{user_input}'")
                return None, False
            
            # Для шага высоты потолка
            if step == "ceiling_height":
                try:
                    # Извлекаем число из строки, заменяя запятую на точку
                    user_input = user_input.replace(',', '.')
                    height_match = re.search(r'(\d+[.,]?\d*)', user_input)
                    if height_match:
                        height = float(height_match.group(1))
                        lighting_logger.info(f"Распознана высота потолка: {height} м")
                        return height, True
                    else:
                        lighting_logger.warning(f"Не удалось распознать высоту в '{user_input}'")
                        return None, False
                except Exception as e:
                    lighting_logger.error(f"Ошибка при обработке высоты потолка: {str(e)}")
                    return None, False
            
            # Для шагов с количеством светильников
            if step in ["light_fixtures", "chandelier", "spot_lights", "wall_lights"]:
                try:
                    # Ищем число в ответе
                    count_match = re.search(r'(\d+)', user_input)
                    if count_match:
                        count = int(count_match.group(1))
                        lighting_logger.info(f"Распознано количество для {step}: {count}")
                        return count, True
                    elif "нет" in user_input.lower() or "не" in user_input.lower() or "0" in user_input:
                        lighting_logger.info(f"Распознано 'нет' для {step}, возвращаем 0")
                        return 0, True
                    else:
                        lighting_logger.warning(f"Не удалось распознать количество в '{user_input}'")
                        return None, False
                except Exception as e:
                    lighting_logger.error(f"Ошибка при обработке количества: {str(e)}")
                    return None, False
            
            # Для неизвестных шагов возвращаем ввод пользователя как есть
            lighting_logger.info(f"Неизвестный шаг {step}, возвращаем ввод как есть")
            return user_input, True
            
        except Exception as e:
            # Перехватываем все ошибки для надежности
            lighting_logger.error(f"Ошибка в match_user_input для {step}: {str(e)}")
            lighting_logger.error(traceback.format_exc())
            
            # Возвращаем значения по умолчанию
            if step == "property_type":
                return "apartment", True
            elif step == "wall_material":
                return "brick", True
            elif step == "ceiling_type":
                return "regular", True
            elif step == "ceiling_height":
                return 2.7, True
            elif step == "complexity":
                return "standard", True
            elif step in ["light_fixtures", "chandelier", "spot_lights", "wall_lights"]:
                return 0, True
            else:
                return user_input, True
    
    def calculate(self, data):
        """
        Рассчитывает стоимость монтажа освещения
        """
        lighting_logger.info(f"Запуск calculate с данными: {data}")
        
        try:
            # Установка значений по умолчанию для обязательных параметров
            property_type = data.get("property_type", "apartment")
            wall_material = data.get("wall_material", "brick")
            ceiling_type = data.get("ceiling_type", "regular")
            complexity = data.get("complexity", "standard")
            
            # Установка значения высоты потолка
            ceiling_height = data.get("ceiling_height", 2.7)
            try:
                ceiling_height = float(ceiling_height)
            except (ValueError, TypeError):
                lighting_logger.warning(f"Не удалось преобразовать высоту потолка '{ceiling_height}' в число, используем 2.7")
                ceiling_height = 2.7
            
            # Конвертация чисел с безопасными значениями по умолчанию
            def safe_int(value, default=0):
                try:
                    return int(value)
                except (ValueError, TypeError):
                    lighting_logger.warning(f"Не удалось преобразовать {value} в целое число, используем {default}")
                    return default
            
            chandelier_count = safe_int(data.get("chandelier", 0))
            spot_lights_count = safe_int(data.get("spot_lights", 0))
            wall_lights_count = safe_int(data.get("wall_lights", 0))
            
            # Если общее количество светильников не указано, вычисляем его
            total_lights = safe_int(data.get("light_fixtures", 0))
            if total_lights == 0:
                total_lights = chandelier_count + spot_lights_count + wall_lights_count
            
            # Проверка на корректные значения
            if property_type not in PROPERTY_TYPE_NAMES:
                lighting_logger.warning(f"Неизвестный тип объекта: {property_type}, используем 'apartment'")
                property_type = "apartment"
                
            if wall_material not in WALL_MATERIAL_COEFFICIENTS:
                lighting_logger.warning(f"Неизвестный материал стен: {wall_material}, используем 'brick'")
                wall_material = "brick"
                
            if complexity not in COMPLEXITY_COEFFICIENTS:
                lighting_logger.warning(f"Неизвестная сложность: {complexity}, используем 'standard'")
                complexity = "standard"
            
            # Коэффициент высоты потолка (увеличиваем стоимость для высоких потолков)
            height_coefficient = 1.0
            if ceiling_height > 3.0:
                height_coefficient = 1.3
            elif ceiling_height > 2.7:
                height_coefficient = 1.15
            
            # Коэффициент типа потолка
            ceiling_coefficient = 1.0
            if ceiling_type == "drywall":
                ceiling_coefficient = 1.2
            elif ceiling_type == "stretch":
                ceiling_coefficient = 1.1
            elif ceiling_type == "suspended":
                ceiling_coefficient = 1.3
            
            # Получаем коэффициенты
            complexity_coefficient = COMPLEXITY_COEFFICIENTS.get(complexity, 1.0)
            wall_coefficient = WALL_MATERIAL_COEFFICIENTS.get(wall_material, 1.0)
            
            # Рассчитываем стоимость
            total_price = 0
            fixtures = {
                "chandelier": chandelier_count,
                "spot_light": spot_lights_count,
                "wall_light": wall_lights_count
            }
            
            fixture_prices = {}
            
            for fixture_type, count in fixtures.items():
                if count > 0 and fixture_type in LIGHTING_PRICES:
                    price_per_unit = LIGHTING_PRICES.get(fixture_type, 0)
                    fixture_price = price_per_unit * count * complexity_coefficient * wall_coefficient * height_coefficient * ceiling_coefficient
                    total_price += fixture_price
                    
                    # Сохраняем цену для каждого типа светильника
                    fixture_prices[fixture_type] = {
                        "count": count,
                        "price_per_unit": price_per_unit,
                        "total_price": round(fixture_price)
                    }
            
            # Если нет расчета ни по одному типу светильника, но есть общее количество
            if not fixture_prices and total_lights > 0:
                avg_price = LIGHTING_PRICES.get("spot_light", 800)  # Средняя цена по умолчанию
                total_price = avg_price * total_lights * complexity_coefficient * wall_coefficient * height_coefficient * ceiling_coefficient
                
                fixture_prices["general"] = {
                    "count": total_lights,
                    "price_per_unit": avg_price,
                    "total_price": round(total_price)
                }
            
            # Формируем результат
            result = {
                "property_type": property_type,
                "wall_material": wall_material,
                "ceiling_type": ceiling_type,
                "ceiling_height": ceiling_height,
                "complexity": complexity,
                "fixtures": fixtures,
                "fixture_prices": fixture_prices,
                "total_lights": total_lights,
                "total_price": round(total_price),
                "price": round(total_price)  # Для совместимости с другими калькуляторами
            }
            
            lighting_logger.info(f"Расчет успешно завершен, результат: {result}")
            return result
            
        except Exception as e:
            lighting_logger.error(f"Ошибка при расчете: {str(e)}")
            lighting_logger.error(traceback.format_exc())
            
            # Возвращаем базовый результат в случае ошибки
            return {
                "property_type": data.get("property_type", "apartment"),
                "wall_material": data.get("wall_material", "brick"),
                "ceiling_type": data.get("ceiling_type", "regular"),
                "ceiling_height": data.get("ceiling_height", 2.7),
                "complexity": "standard",
                "total_lights": 0,
                "total_price": 0,
                "price": 0,
                "fixture_prices": {},
                "fixtures": {}
            }
    
    def format_result(self, calculation):
        """
        Форматирует результат расчета в читаемый текст
        """
        lighting_logger.info("Запуск format_result")
        
        try:
            # Получаем удобочитаемые названия для кодов
            property_type = get_formatted_name(PROPERTY_TYPE_NAMES, calculation.get('property_type', 'apartment'))
            wall_material = get_formatted_name(WALL_MATERIAL_NAMES, calculation.get('wall_material', 'brick'))
            complexity = get_formatted_name(COMPLEXITY_LEVEL_NAMES, calculation.get('complexity', 'standard'))
            
            # Названия для типов потолков
            ceiling_types = {
                "regular": "Обычный (бетонная плита)",
                "drywall": "Гипсокартонный",
                "stretch": "Натяжной",
                "suspended": "Подвесной (Армстронг и т.п.)"
            }
            ceiling_type = ceiling_types.get(calculation.get('ceiling_type', 'regular'), 'Обычный')
            
            # Названия для типов светильников
            fixture_names = {
                "chandelier": "Люстры/подвесные светильники",
                "spot_light": "Точечные светильники",
                "wall_light": "Настенные светильники",
                "general": "Светильники"
            }
            
            # Форматируем текст результата
            result = "📋 Расчет стоимости монтажа освещения:\n\n"
            
            # Основные параметры
            result += f"• Тип объекта: {property_type}\n"
            result += f"• Материал стен: {wall_material}\n"
            result += f"• Тип потолка: {ceiling_type}\n"
            result += f"• Высота потолков: {calculation.get('ceiling_height', 2.7)} м\n"
            result += f"• Сложность монтажа: {complexity}\n\n"
            
            # Если есть выбранные светильники
            if calculation.get("total_lights", 0) > 0:
                result += "Светильники:\n"
                
                for fixture_type, details in calculation.get("fixture_prices", {}).items():
                    fixture_name = fixture_names.get(fixture_type, "Светильники")
                    result += f"• {fixture_name}: {details['count']} шт. x {details['price_per_unit']} руб. = {details['total_price']} руб.\n"
                
                result += f"\nВсего светильников: {calculation.get('total_lights', 0)} шт.\n"
            else:
                result += "Светильники не выбраны.\n"
            
            # Итоговая стоимость
            result += f"\n💰 Общая стоимость монтажа: {calculation.get('total_price', 0)} руб.\n"
            
            # Добавляем важное примечание
            result += "\n⚠️ ВНИМАНИЕ: Это предварительная оценка стоимости монтажа освещения. "
            result += "Точная стоимость определяется после выезда специалиста на объект и уточнения деталей заказа. "
            result += "Цена может измениться в зависимости от сложности работ и других особенностей объекта."
            
            lighting_logger.info("format_result успешно завершен")
            return result
        
        except Exception as e:
            lighting_logger.error(f"Ошибка в format_result: {str(e)}")
            lighting_logger.error(traceback.format_exc())
            
            # В случае ошибки возвращаем простой результат
            return f"Результат расчета: {calculation.get('total_price', 0)} руб.\n\nПожалуйста, обратитесь к менеджеру для получения детальной информации."


# Функции для интеграции с диспетчером калькуляторов

def start_lighting_calculation(session_id, chat_states, initial_data=None):
    """
    Запускает калькулятор монтажа освещения
    """
    lighting_logger.info(f"Запуск калькулятора освещения для сессии {session_id}")
    try:
        return BaseCalculatorDialog.start_dialog(LightingCalculator, session_id, chat_states, initial_data)
    except Exception as e:
        lighting_logger.error(f"Ошибка при запуске калькулятора освещения: {str(e)}")
        lighting_logger.error(traceback.format_exc())
        return "К сожалению, произошла ошибка при запуске калькулятора. Пожалуйста, попробуйте еще раз или обратитесь к менеджеру."

def process_lighting_calculation(user_input, session_id, chat_states):
    """
    Обрабатывает ввод пользователя в диалоге калькулятора освещения
    """
    lighting_logger.info(f"Обработка ввода '{user_input}' для сессии {session_id}")
    try:
        # Если нужно отменить расчет
        if user_input.lower() in ["отмена", "стоп", "прервать", "отменить"]:
            if session_id in chat_states:
                del chat_states[session_id]
            lighting_logger.info(f"Расчет отменен для сессии {session_id}")
            return "Расчет стоимости отменен. Чем еще я могу вам помочь?"
            
        # Специальная обработка для шага сложности
        if (session_id in chat_states and 
            chat_states[session_id].get("stage") == "complexity" and 
            user_input.strip() in ["1", "2", "3", "4"]):
            
            lighting_logger.info(f"Обнаружен выбор сложности: '{user_input}'")
            
            # Маппинг выбора сложности на текстовые значения
            complexity_map = {
                "1": "easy",
                "2": "standard",
                "3": "complex",
                "4": "very_complex"
            }
            complexity_text_map = {
                "1": "Простой монтаж",
                "2": "Стандартная сложность",
                "3": "Сложный монтаж",
                "4": "Очень сложный монтаж"
            }
            
            # Устанавливаем выбранную сложность
            complexity = complexity_map.get(user_input.strip(), "standard")
            chat_states[session_id]["data"]["complexity"] = complexity
            
            # Сохраняем текстовое значение выбора для отображения
            chat_states[session_id]["complexity_answer"] = complexity_text_map.get(user_input.strip(), "Стандартная сложность")
            
            # Отмечаем этап как завершенный
            chat_states[session_id]["stage"] = "completed"
            
            # Производим расчет
            calculator = LightingCalculator()
            calculation = calculator.calculate(chat_states[session_id]["data"])
            result = calculator.format_result(calculation)
            
            # Сохраняем результат
            chat_states[session_id]["calculation_result"] = result
            chat_states[session_id]["full_calc"] = calculation
            
            # Возвращаем результат с запросом контактных данных
            contact_request = "\n\nХотите получить точный расчет и консультацию специалиста? Пожалуйста, оставьте свои контактные данные (имя, телефон, email), и наш мастер свяжется с вами в ближайшее время.[SHOW_CONTACT_FORM]"
            return result + contact_request
            
        # Стандартная обработка
        return BaseCalculatorDialog.process_dialog(LightingCalculator, user_input, session_id, chat_states)
        
    except Exception as e:
        lighting_logger.error(f"Ошибка при обработке ввода: {str(e)}")
        lighting_logger.error(traceback.format_exc())
        
        # Сбрасываем состояние в случае критической ошибки
        if session_id in chat_states:
            del chat_states[session_id]
            
        return "К сожалению, произошла ошибка при обработке вашего запроса. Пожалуйста, начните расчет заново или обратитесь к менеджеру по телефону +7(909) 617-97-63."