# calculator/industrial_calculator.py
# Калькулятор для расчета стоимости электромонтажа промышленных объектов

import logging
import re
from datetime import datetime
from .base_calculator import BaseCalculator, BaseCalculatorDialog
from .services_prices import (
    AREA_RATES, MIN_AREAS, COMPLEXITY_COEFFICIENTS,
    PROPERTY_TYPE_NAMES, COMPLEXITY_LEVEL_NAMES, get_formatted_name
)

class IndustrialCalculator(BaseCalculator):
    """
    Калькулятор для расчета стоимости электромонтажа промышленных объектов
    """
    
    # Переопределяем константы базового класса
    NAME = "Электроснабжение промышленных объектов"
    TYPE = "industrial"
    
    # Коэффициенты для типов промышленных объектов
    INDUSTRIAL_TYPE_COEFFICIENTS = {
        "workshop": 1.0,     # Производственный цех
        "warehouse": 0.85,   # Склад
        "laboratory": 1.2,   # Лаборатория
        "plant": 1.5,        # Завод/большое предприятие
        "logistics": 0.9     # Логистический центр
    }
    
    # Коэффициенты для мощности объекта
    POWER_COEFFICIENTS = {
        "up_to_50": 0.8,     # До 50 кВт
        "50_to_150": 1.0,    # От 50 до 150 кВт
        "150_to_400": 1.3,   # От 150 до 400 кВт
        "400_plus": 1.6      # Более 400 кВт
    }
    
    # Цены на промышленное оборудование
    INDUSTRIAL_EQUIPMENT_PRICES = {
        "transformer": 85000,      # Трансформаторная подстанция
        "distribution_panel": 45000, # Распределительный щит
        "standby_generator": 120000, # Резервный генератор
        "ups": 65000,             # ИБП (система бесперебойного питания)
        "power_cable": 2500,      # Силовой кабель (за метр погонный)
        "grounding": 35000,       # Система заземления
        "lightning_protection": 30000, # Молниезащита
        "automation": 70000       # Система автоматизации
    }
    
    # Названия типов промышленных объектов
    INDUSTRIAL_TYPE_NAMES = {
        "workshop": "производственный цех",
        "warehouse": "склад",
        "laboratory": "лаборатория",
        "plant": "завод/крупное предприятие",
        "logistics": "логистический центр"
    }
    
    # Названия мощностей
    POWER_NAMES = {
        "up_to_50": "до 50 кВт",
        "50_to_150": "от 50 до 150 кВт",
        "150_to_400": "от 150 до 400 кВт",
        "400_plus": "более 400 кВт"
    }
    
    # Названия промышленного оборудования
    INDUSTRIAL_EQUIPMENT_NAMES = {
        "transformer": "Трансформаторная подстанция",
        "distribution_panel": "Распределительный щит",
        "standby_generator": "Резервный генератор",
        "ups": "Система бесперебойного питания (ИБП)",
        "power_cable": "Силовой кабель (за метр погонный)",
        "grounding": "Система заземления",
        "lightning_protection": "Система молниезащиты",
        "automation": "Система автоматизации"
    }
    
    # Определяем шаги диалога для этого калькулятора
    DIALOG_STEPS = [
        "industrial_type",
        "area",
        "power",
        "equipment",
        "complexity",
        "power_cable_length"
    ]
    
    # Определяем сообщения для каждого шага
    STEP_MESSAGES = {
        "industrial_type": ("Выберите тип промышленного объекта:\n"
                          "1. Производственный цех\n"
                          "2. Склад\n"
                          "3. Лаборатория\n"
                          "4. Завод/крупное предприятие\n"
                          "5. Логистический центр"),
        
        "area": "Укажите площадь объекта в квадратных метрах:",
        
        "power": ("Выберите потребляемую мощность объекта:\n"
                 "1. До 50 кВт\n"
                 "2. От 50 до 150 кВт\n"
                 "3. От 150 до 400 кВт\n"
                 "4. Более 400 кВт"),
        
        "equipment": ("Выберите необходимое оборудование (можно выбрать несколько, введите номера через запятую):\n"
                     "1. Трансформаторная подстанция\n"
                     "2. Распределительный щит\n"
                     "3. Резервный генератор\n"
                     "4. Система бесперебойного питания (ИБП)\n"
                     "5. Система заземления\n"
                     "6. Система молниезащиты\n"
                     "7. Система автоматизации\n"
                     "0. Ничего из вышеперечисленного"),
        
        "complexity": ("Выберите сложность монтажа:\n"
                      "1. Стандартная сложность\n"
                      "2. Повышенная сложность (специфические требования)\n"
                      "3. Высокая сложность (особые условия, специальное оборудование)"),
        
        "power_cable_length": "Укажите примерную длину силового кабеля в метрах (если неизвестно, оставьте пустым):"
    }
    
    # Определяем соответствия для ответов пользователя
    USER_INPUT_MAPPINGS = {
        "industrial_type": {
            "1": "workshop", "цех": "workshop", "производств": "workshop",
            "2": "warehouse", "склад": "warehouse",
            "3": "laboratory", "лаборатор": "laboratory",
            "4": "plant", "завод": "plant", "предприя": "plant",
            "5": "logistics", "логистич": "logistics"
        },
        
        "power": {
            "1": "up_to_50", "до 50": "up_to_50",
            "2": "50_to_150", "от 50 до 150": "50_to_150",
            "3": "150_to_400", "от 150 до 400": "150_to_400",
            "4": "400_plus", "более 400": "400_plus", "выше 400": "400_plus"
        },
        
        "complexity": {
            "1": "standard", "стандарт": "standard",
            "2": "complex", "повышен": "complex", "специфич": "complex",
            "3": "very_complex", "высок": "very_complex", "особ": "very_complex"
        }
    }
    
    @classmethod
    def match_user_input(cls, step, user_input):
        """
        Переопределяем метод сопоставления для специфических шагов
        """
        # Используем стандартное сопоставление для шагов, определенных в USER_INPUT_MAPPINGS
        if step in cls.USER_INPUT_MAPPINGS:
            return super().match_user_input(step, user_input)
        
        # Для специфических шагов этого калькулятора
        if step == "equipment":
            # Обрабатываем выбор оборудования
            equipment_mapping = {
                "1": "transformer",
                "2": "distribution_panel",
                "3": "standby_generator",
                "4": "ups",
                "5": "grounding",
                "6": "lightning_protection",
                "7": "automation"
            }
            
            selected_equipment = []
            
            # Проверяем на отказ от выбора
            if "0" in user_input or "ничего" in user_input.lower() or "нет" in user_input.lower():
                # Пользователь выбрал "Ничего из вышеперечисленного"
                return [], True
            
            # Ищем числа в ответе
            numbers = re.findall(r'(\d+)', user_input)
            
            for num in numbers:
                if num in equipment_mapping:
                    equipment = equipment_mapping[num]
                    selected_equipment.append(equipment)
            
            # Также проверяем ключевые слова
            keyword_mapping = {
                "трансформатор": "transformer", "подстанц": "transformer",
                "распредел": "distribution_panel", "щит": "distribution_panel",
                "генератор": "standby_generator", "резерв": "standby_generator",
                "ибп": "ups", "бесперебой": "ups",
                "заземлен": "grounding", "земл": "grounding",
                "молни": "lightning_protection", "грозо": "lightning_protection",
                "автоматиз": "automation", "автоматик": "automation"
            }
            
            for keyword, equip in keyword_mapping.items():
                if keyword in user_input.lower() and equip not in selected_equipment:
                    selected_equipment.append(equip)
            
            return selected_equipment, True
            
        elif step == "power_cable_length":
            # Парсим длину кабеля (необязательный параметр)
            if not user_input.strip():
                return None, True  # Пустой ответ допустим
            
            try:
                length = float(re.search(r'(\d+(?:\.\d+)?)', user_input).group(1))
                if length <= 0:
                    return None, False
                return length, True
            except:
                return None, False
        
        # Для неизвестных шагов возвращаем ввод пользователя как есть
        return user_input, True
    
    def calculate(self, data):
        """
        Рассчитывает стоимость электромонтажа промышленного объекта
        
        Args:
            data (dict): Данные для расчета
            
        Returns:
            dict: Результат расчета
        """
        # Получаем необходимые параметры из данных
        industrial_type = data.get("industrial_type", "workshop")
        area = data.get("area", 0)
        power = data.get("power", "50_to_150")
        equipment = data.get("equipment", [])
        complexity = data.get("complexity", "standard")
        power_cable_length = data.get("power_cable_length")
        
        # Проверяем наличие обязательных параметров
        required_params = ["industrial_type", "area", "power", "complexity"]
        for param in required_params:
            if param not in data:
                raise ValueError(f"Не указан обязательный параметр: {param}")
        
        # Проверка исходных данных
        if industrial_type not in self.INDUSTRIAL_TYPE_COEFFICIENTS:
            raise ValueError(f"Неизвестный тип промышленного объекта: {industrial_type}")
            
        if power not in self.POWER_COEFFICIENTS:
            raise ValueError(f"Неизвестная мощность объекта: {power}")
            
        if complexity not in COMPLEXITY_COEFFICIENTS:
            raise ValueError(f"Неизвестная сложность монтажа: {complexity}")
        
        # Убеждаемся, что площадь не меньше минимальной для промышленных объектов
        min_area = MIN_AREAS.get("industrial", 20)
        if area < min_area:
            area = min_area
        
        # Получаем базовую ставку и коэффициенты
        base_rate = AREA_RATES["industrial"]  # Используем ставку для промышленных объектов
        industrial_coefficient = self.INDUSTRIAL_TYPE_COEFFICIENTS[industrial_type]
        power_coefficient = self.POWER_COEFFICIENTS[power]
        complexity_coefficient = COMPLEXITY_COEFFICIENTS[complexity]
        
        # Базовая стоимость электромонтажа промышленного объекта
        base_price = area * base_rate * industrial_coefficient * power_coefficient * complexity_coefficient
        
        # Стоимость оборудования
        equipment_price = 0
        equipment_prices = {}
        
        for equip in equipment:
            if equip in self.INDUSTRIAL_EQUIPMENT_PRICES:
                price = self.INDUSTRIAL_EQUIPMENT_PRICES[equip]
                
                # Для силового кабеля нужно учесть длину
                if equip == "power_cable" and power_cable_length:
                    price = price * power_cable_length
                
                equipment_price += price
                equipment_prices[equip] = price
        
        # Если силовой кабель не выбран, но длина указана, добавляем его
        if "power_cable" not in equipment and power_cable_length:
            price = self.INDUSTRIAL_EQUIPMENT_PRICES["power_cable"] * power_cable_length
            equipment_price += price
            equipment_prices["power_cable"] = price
            equipment.append("power_cable")
        
        # Итоговая стоимость
        total_price = base_price + equipment_price
        
        # Формируем результат
        result = {
            "industrial_type": industrial_type,
            "area": area,
            "power": power,
            "equipment": equipment,
            "complexity": complexity,
            "power_cable_length": power_cable_length,
            "base_price": round(base_price),
            "equipment_price": equipment_price,
            "equipment_prices": equipment_prices,
            "total_price": round(total_price),
            "price": round(total_price)  # Для совместимости с другими калькуляторами
        }
        
        return result
    
    def format_result(self, calculation):
        """
        Форматирует результат расчета в читаемый текст
        
        Args:
            calculation (dict): Результат расчета
            
        Returns:
            str: Форматированный текст
        """
        # Получаем удобочитаемые названия для кодов
        industrial_type = get_formatted_name(self.INDUSTRIAL_TYPE_NAMES, calculation['industrial_type'])
        power = get_formatted_name(self.POWER_NAMES, calculation['power'])
        complexity = get_formatted_name(COMPLEXITY_LEVEL_NAMES, calculation['complexity'])
        
        # Форматируем текст результата
        result = "📋 Расчет стоимости электроснабжения промышленного объекта:\n\n"
        
        # Основные параметры
        result += f"• Тип объекта: {industrial_type}\n"
        result += f"• Площадь: {calculation['area']} кв.м\n"
        result += f"• Потребляемая мощность: {power}\n"
        result += f"• Сложность монтажа: {complexity}\n"
        
        # Информация о выбранном оборудовании
        if calculation['equipment']:
            result += "\nВыбранное оборудование:\n"
            for equip in calculation['equipment']:
                equipment_name = get_formatted_name(self.INDUSTRIAL_EQUIPMENT_NAMES, equip)
                equipment_price = calculation['equipment_prices'].get(equip, 0)
                
                # Для силового кабеля указываем длину
                if equip == "power_cable" and calculation.get('power_cable_length'):
                    equipment_name += f" ({calculation['power_cable_length']} м)"
                
                result += f"• {equipment_name}: {equipment_price} руб.\n"
        
        # Стоимость
        result += f"\n• Базовая стоимость работ: {calculation['base_price']} руб.\n"
        
        if calculation['equipment_price'] > 0:
            result += f"• Стоимость оборудования: {calculation['equipment_price']} руб.\n"
        
        result += f"• Общая стоимость: {calculation['total_price']} руб.\n"
        
        # Добавляем важное примечание
        result += "\n⚠️ ВНИМАНИЕ: Это предварительная оценка стоимости электроснабжения промышленного объекта. "
        result += "Для составления точной сметы необходим выезд специалистов на объект, изучение документации "
        result += "и проведение технического обследования. Окончательная стоимость может существенно отличаться "
        result += "в зависимости от особенностей объекта, требований к электроснабжению и других факторов."
        
        return result


# Функции для интеграции с диспетчером калькуляторов

def start_industrial_calculation(session_id, chat_states, initial_data=None):
    """
    Запускает калькулятор для промышленных объектов
    
    Args:
        session_id (str): Идентификатор сессии
        chat_states (dict): Словарь состояний чата
        initial_data (dict, optional): Начальные данные
        
    Returns:
        str: Первое сообщение калькулятора
    """
    return BaseCalculatorDialog.start_dialog(IndustrialCalculator, session_id, chat_states, initial_data)

def process_industrial_calculation(user_input, session_id, chat_states):
    """
    Обрабатывает ввод пользователя в диалоге калькулятора для промышленных объектов
    
    Args:
        user_input (str): Сообщение пользователя
        session_id (str): Идентификатор сессии
        chat_states (dict): Словарь состояний чата
        
    Returns:
        str: Ответ калькулятора
    """
    return BaseCalculatorDialog.process_dialog(IndustrialCalculator, user_input, session_id, chat_states)