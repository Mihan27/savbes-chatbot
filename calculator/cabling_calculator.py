# calculator/cabling_calculator.py
# Калькулятор стоимости прокладки кабеля

import logging
import re
from datetime import datetime
from .base_calculator import BaseCalculator, BaseCalculatorDialog
from .services_prices import (
    AREA_RATES, MIN_AREAS, COMPLEXITY_COEFFICIENTS,
    CABLING_PRICES, CABLING_TYPE_NAMES, WALL_MATERIAL_COEFFICIENTS, 
    CABLE_SECTION_COEFFICIENTS, COMPLEXITY_LEVEL_NAMES,
    PROPERTY_TYPE_NAMES, WALL_MATERIAL_NAMES, get_formatted_name
)

class CablingCalculator(BaseCalculator):
    """Калькулятор для расчета стоимости прокладки кабелей и проводки"""
    
    # Переопределяем константы базового класса
    NAME = "Прокладка кабеля и проводки"
    TYPE = "cabling"
    
    # Определяем шаги диалога для этого калькулятора
    DIALOG_STEPS = [
        "property_type",
        "area",
        "wall_material",
        "cabling_type",
        "cable_length",
        "cable_section",
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
        
        "area": "Укажите площадь помещения в квадратных метрах:",
        
        "wall_material": ("Выберите материал стен:\n"
                         "1. Гипсокартон\n"
                         "2. Кирпич\n"
                         "3. Бетон\n"
                         "4. Дерево\n"
                         "5. Газоблок/пеноблок"),
        
        "cabling_type": ("Выберите тип прокладки кабеля:\n"
                        "1. Открытая проводка\n"
                        "2. Скрытая проводка\n"
                        "3. Проводка в кабель-канале\n"
                        "4. Проводка в гофре\n"
                        "5. Подземная прокладка\n"
                        "6. Воздушная прокладка"),
        
        "cable_length": "Укажите примерную длину кабеля в метрах (если неизвестно, оставьте пустым):",
        
        "cable_section": ("Выберите сечение кабеля:\n"
                         "1. 1.5 мм²\n"
                         "2. 2.5 мм²\n"
                         "3. 4.0 мм²\n"
                         "4. 6.0 мм²\n"
                         "5. 10.0 мм²"),
        
        "complexity": ("Выберите сложность прокладки кабеля:\n"
                      "1. Простой монтаж (прямые пути, хороший доступ)\n"
                      "2. Стандартная сложность\n"
                      "3. Сложный монтаж (труднодоступные места, препятствия)")
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
        
        "cabling_type": {
            "1": "open", "открыт": "open",
            "2": "hidden", "скрыт": "hidden",
            "3": "cable_channel", "канал": "cable_channel", "короб": "cable_channel",
            "4": "corrugation", "гофр": "corrugation",
            "5": "ground", "подземн": "ground", "земл": "ground",
            "6": "overhead", "воздуш": "overhead"
        },
        
        "cable_section": {
            "1": "1.5", "1,5": "1.5",
            "2": "2.5", "2,5": "2.5",
            "3": "4.0", "4,0": "4.0", "4": "4.0",
            "4": "6.0", "6,0": "6.0", "6": "6.0",
            "5": "10.0", "10,0": "10.0", "10": "10.0"
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
        # Используем стандартное сопоставление для шагов, определенных в USER_INPUT_MAPPINGS
        if step in cls.USER_INPUT_MAPPINGS:
            return super().match_user_input(step, user_input)
        
        # Для специфических шагов этого калькулятора
        if step == "cable_length":
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
        Рассчитывает стоимость прокладки кабеля
        
        Args:
            data (dict): Данные для расчета
            
        Returns:
            dict: Результат расчета
        """
        # Получаем необходимые параметры из данных
        property_type = data.get("property_type", "apartment")
        area = data.get("area", 0)
        wall_material = data.get("wall_material", "brick")
        cabling_type = data.get("cabling_type", "hidden")
        cable_length = data.get("cable_length")
        cable_section = data.get("cable_section", "2.5")
        complexity = data.get("complexity", "standard")
        
        # Проверяем наличие обязательных параметров
        required_params = ["property_type", "area", "cabling_type", "complexity"]
        for param in required_params:
            if param not in data:
                raise ValueError(f"Не указан обязательный параметр: {param}")
        
        # Проверка исходных данных
        if cabling_type not in CABLING_PRICES:
            raise ValueError(f"Неизвестный тип прокладки кабеля: {cabling_type}")
            
        if complexity not in COMPLEXITY_COEFFICIENTS:
            raise ValueError(f"Неизвестная сложность: {complexity}")
            
        if property_type not in AREA_RATES:
            raise ValueError(f"Неизвестный тип помещения: {property_type}")
            
        if wall_material not in WALL_MATERIAL_COEFFICIENTS:
            raise ValueError(f"Неизвестный материал стен: {wall_material}")
        
        # Убеждаемся, что площадь не меньше минимальной
        min_area = MIN_AREAS.get(property_type, 5)
        if area < min_area:
            area = min_area
        
        # Получаем базовую ставку и коэффициенты
        base_price_per_meter = CABLING_PRICES[cabling_type]
        complexity_coefficient = COMPLEXITY_COEFFICIENTS[complexity]
        wall_coefficient = WALL_MATERIAL_COEFFICIENTS[wall_material]
        cable_section_coefficient = CABLE_SECTION_COEFFICIENTS.get(cable_section, 1.0)
        
        # Если длина кабеля указана явно
        if cable_length:
            # Используем указанную длину
            total_length = cable_length
        else:
            # Оцениваем длину кабеля на основе площади помещения
            # Для скрытой проводки требуется больше кабеля
            if cabling_type == "hidden":
                total_length = area * 1.2
            else:
                total_length = area * 0.8
        
        # Итоговая стоимость
        price = total_length * base_price_per_meter * complexity_coefficient * wall_coefficient * cable_section_coefficient
        
        # Формируем результат
        result = {
            "property_type": property_type,
            "area": area,
            "wall_material": wall_material,
            "cabling_type": cabling_type,
            "cable_length": total_length,
            "cable_section": cable_section,
            "complexity": complexity,
            "price_per_meter": base_price_per_meter,
            "total_price": round(price),
            "price": round(price)  # Для совместимости с другими калькуляторами
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
        property_type = get_formatted_name(PROPERTY_TYPE_NAMES, calculation['property_type'])
        wall_material = get_formatted_name(WALL_MATERIAL_NAMES, calculation['wall_material'])
        cabling_type = get_formatted_name(CABLING_TYPE_NAMES, calculation['cabling_type'])
        complexity = get_formatted_name(COMPLEXITY_LEVEL_NAMES, calculation['complexity'])
        
        # Форматируем текст результата
        result = "📋 Расчет стоимости прокладки кабеля и проводки:\n\n"
        
        # Основные параметры
        result += f"• Тип объекта: {property_type}\n"
        result += f"• Площадь: {calculation['area']} кв.м\n"
        result += f"• Материал стен: {wall_material}\n"
        result += f"• Тип прокладки кабеля: {cabling_type}\n"
        result += f"• Примерная длина кабеля: {round(calculation['cable_length'])} м\n"
        result += f"• Сечение кабеля: {calculation['cable_section']} мм²\n"
        result += f"• Сложность монтажа: {complexity}\n\n"
        
        # Стоимость
        result += f"• Базовая стоимость за метр: {calculation['price_per_meter']} руб.\n"
        result += f"• Общая стоимость: {calculation['total_price']} руб.\n"
        
        # Добавляем важное примечание
        result += "\n⚠️ ВНИМАНИЕ: Это предварительная оценка стоимости прокладки кабеля. "
        result += "Для более точного расчета необходим выезд специалиста на объект для оценки "
        result += "фактических условий работы. Окончательная стоимость может отличаться в зависимости "
        result += "от особенностей объекта и дополнительных работ."
        
        return result


# Функции для интеграции с диспетчером калькуляторов

def start_cabling_calculation(session_id, chat_states, initial_data=None):
    """
    Запускает калькулятор прокладки кабеля
    
    Args:
        session_id (str): Идентификатор сессии
        chat_states (dict): Словарь состояний чата
        initial_data (dict, optional): Начальные данные
        
    Returns:
        str: Первое сообщение калькулятора
    """
    return BaseCalculatorDialog.start_dialog(CablingCalculator, session_id, chat_states, initial_data)

def process_cabling_calculation(user_input, session_id, chat_states):
    """
    Обрабатывает ввод пользователя в диалоге калькулятора прокладки кабеля
    
    Args:
        user_input (str): Сообщение пользователя
        session_id (str): Идентификатор сессии
        chat_states (dict): Словарь состояний чата
        
    Returns:
        str: Ответ калькулятора
    """
    return BaseCalculatorDialog.process_dialog(CablingCalculator, user_input, session_id, chat_states)