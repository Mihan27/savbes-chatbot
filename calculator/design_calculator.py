# calculator/design_calculator.py
# Калькулятор стоимости электромонтажа по дизайн-проекту

import logging
import re
from datetime import datetime
from .base_calculator import BaseCalculator, BaseCalculatorDialog
from .services_prices import (
    AREA_RATES, MIN_AREAS, COMPLEXITY_COEFFICIENTS,
    PROPERTY_TYPE_NAMES, COMPLEXITY_LEVEL_NAMES, get_formatted_name
)

class DesignCalculator(BaseCalculator):
    """Калькулятор для расчета стоимости электромонтажа по дизайнерскому проекту"""
    
    # Переопределяем константы базового класса
    NAME = "Электромонтаж по дизайн-проекту"
    TYPE = "design"
    
    # Коэффициенты сложности дизайн-проекта
    DESIGN_COMPLEXITY_COEFFICIENTS = {
        "simple": 1.2,      # Простой дизайн-проект
        "standard": 1.5,    # Стандартный дизайн-проект
        "complex": 2.0,     # Сложный дизайн-проект
        "premium": 2.5      # Премиальный дизайн-проект
    }
    
    # Названия сложности дизайн-проекта
    DESIGN_COMPLEXITY_NAMES = {
        "simple": "простой дизайн-проект",
        "standard": "стандартный дизайн-проект",
        "complex": "сложный дизайн-проект",
        "premium": "премиальный дизайн-проект"
    }
    
    # Определяем шаги диалога для этого калькулятора
    DIALOG_STEPS = [
        "property_type",
        "area",
        "design_complexity",
        "has_project",
        "implementation_complexity",
        "additional_features"
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
        
        "design_complexity": ("Выберите сложность дизайн-проекта:\n"
                            "1. Простой (стандартные решения, минимум декоративных элементов)\n"
                            "2. Стандартный (средний уровень сложности)\n"
                            "3. Сложный (нестандартные решения, много декоративных элементов)\n"
                            "4. Премиальный (авторский дизайн, уникальные решения)"),
        
        "has_project": "У вас уже есть готовый дизайн-проект? (да/нет)",
        
        "implementation_complexity": ("Выберите сложность реализации проекта:\n"
                                   "1. Простая (стандартное расположение, хороший доступ)\n"
                                   "2. Стандартная\n"
                                   "3. Сложная (нестандартное расположение, ограниченный доступ)"),
        
        "additional_features": ("Выберите дополнительные элементы (можно выбрать несколько, введите номера через запятую):\n"
                              "1. Сложное декоративное освещение\n"
                              "2. Умный дом (базовая комплектация)\n"
                              "3. Мультимедиа системы\n"
                              "4. Нестандартные выключатели/розетки\n"
                              "5. Индивидуальная подсветка мебели/ниш\n"
                              "0. Не требуются")
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
        
        "design_complexity": {
            "1": "simple", "прост": "simple",
            "2": "standard", "стандарт": "standard",
            "3": "complex", "сложн": "complex",
            "4": "premium", "премиал": "premium", "авторск": "premium"
        },
        
        "has_project": {
            "да": True, "есть": True, "готов": True, "имеется": True,
            "нет": False, "не имеется": False, "отсутств": False
        },
        
        "implementation_complexity": {
            "1": "easy", "прост": "easy",
            "2": "standard", "стандарт": "standard",
            "3": "complex", "сложн": "complex"
        }
    }
    
    # Стоимость дополнительных элементов
    ADDITIONAL_FEATURES_PRICES = {
        "decorative_lighting": 15000,     # Сложное декоративное освещение
        "smart_home_basic": 45000,        # Умный дом (базовая комплектация)
        "multimedia": 25000,              # Мультимедиа системы
        "custom_switches": 8000,          # Нестандартные выключатели/розетки
        "furniture_lighting": 12000       # Индивидуальная подсветка мебели/ниш
    }
    
    # Названия дополнительных элементов
    ADDITIONAL_FEATURES_NAMES = {
        "decorative_lighting": "Сложное декоративное освещение",
        "smart_home_basic": "Умный дом (базовая комплектация)",
        "multimedia": "Мультимедиа системы",
        "custom_switches": "Нестандартные выключатели/розетки",
        "furniture_lighting": "Индивидуальная подсветка мебели/ниш"
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
        if step == "additional_features":
            # Обрабатываем выбор дополнительных элементов
            feature_mapping = {
                "1": "decorative_lighting",
                "2": "smart_home_basic",
                "3": "multimedia",
                "4": "custom_switches",
                "5": "furniture_lighting"
            }
            
            selected_features = []
            
            # Проверяем на отказ от выбора
            if "0" in user_input or "не треб" in user_input.lower() or "нет" in user_input.lower():
                # Пользователь выбрал "Не требуются"
                return [], True
            
            # Ищем числа в ответе
            numbers = re.findall(r'(\d+)', user_input)
            
            for num in numbers:
                if num in feature_mapping:
                    feature = feature_mapping[num]
                    selected_features.append(feature)
            
            # Также проверяем ключевые слова
            keyword_mapping = {
                "декоратив": "decorative_lighting", "освещен": "decorative_lighting",
                "умн": "smart_home_basic", "умный дом": "smart_home_basic",
                "мультимед": "multimedia", "медиа": "multimedia",
                "нестандарт": "custom_switches", "выключат": "custom_switches", "розет": "custom_switches",
                "подсвет": "furniture_lighting", "мебел": "furniture_lighting", "ниш": "furniture_lighting"
            }
            
            for keyword, feature in keyword_mapping.items():
                if keyword in user_input.lower() and feature not in selected_features:
                    selected_features.append(feature)
            
            return selected_features, True
        
        # Для неизвестных шагов возвращаем ввод пользователя как есть
        return user_input, True
    
    def calculate(self, data):
        """
        Рассчитывает стоимость электромонтажа по дизайн-проекту
        
        Args:
            data (dict): Данные для расчета
            
        Returns:
            dict: Результат расчета
        """
        # Получаем необходимые параметры из данных
        property_type = data.get("property_type", "apartment")
        area = data.get("area", 0)
        design_complexity = data.get("design_complexity", "standard")
        has_project = data.get("has_project", False)
        implementation_complexity = data.get("implementation_complexity", "standard")
        additional_features = data.get("additional_features", [])
        
        # Проверяем наличие обязательных параметров
        required_params = ["property_type", "area", "design_complexity", "implementation_complexity"]
        for param in required_params:
            if param not in data:
                raise ValueError(f"Не указан обязательный параметр: {param}")
        
        # Проверка исходных данных
        if design_complexity not in self.DESIGN_COMPLEXITY_COEFFICIENTS:
            raise ValueError(f"Неизвестная сложность дизайн-проекта: {design_complexity}")
            
        if implementation_complexity not in COMPLEXITY_COEFFICIENTS:
            raise ValueError(f"Неизвестная сложность реализации: {implementation_complexity}")
            
        if property_type not in AREA_RATES:
            raise ValueError(f"Неизвестный тип помещения: {property_type}")
        
        # Убеждаемся, что площадь не меньше минимальной
        min_area = MIN_AREAS.get(property_type, 5)
        if area < min_area:
            area = min_area
        
        # Получаем базовую ставку и коэффициенты
        base_rate = AREA_RATES[property_type]
        design_coefficient = self.DESIGN_COMPLEXITY_COEFFICIENTS[design_complexity]
        implementation_coefficient = COMPLEXITY_COEFFICIENTS[implementation_complexity]
        
        # Если нет готового проекта, добавляем стоимость проектирования
        project_price = 0
        if not has_project:
            project_price = area * 300  # Примерная стоимость проектирования - 300 руб/м²
        
        # Базовая стоимость реализации дизайн-проекта
        base_price = area * base_rate * design_coefficient * implementation_coefficient
        
        # Стоимость дополнительных элементов
        additional_price = 0
        feature_prices = {}
        
        for feature in additional_features:
            if feature in self.ADDITIONAL_FEATURES_PRICES:
                feature_price = self.ADDITIONAL_FEATURES_PRICES[feature]
                additional_price += feature_price
                feature_prices[feature] = feature_price
        
        # Итоговая стоимость
        total_price = base_price + project_price + additional_price
        
        # Формируем результат
        result = {
            "property_type": property_type,
            "area": area,
            "design_complexity": design_complexity,
            "has_project": has_project,
            "implementation_complexity": implementation_complexity,
            "additional_features": additional_features,
            "base_price": round(base_price),
            "project_price": round(project_price),
            "additional_price": additional_price,
            "feature_prices": feature_prices,
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
        property_type = get_formatted_name(PROPERTY_TYPE_NAMES, calculation['property_type'])
        design_complexity = get_formatted_name(self.DESIGN_COMPLEXITY_NAMES, calculation['design_complexity'])
        implementation_complexity = get_formatted_name(COMPLEXITY_LEVEL_NAMES, calculation['implementation_complexity'])
        
        # Форматируем текст результата
        result = "📋 Расчет стоимости электромонтажа по дизайн-проекту:\n\n"
        
        # Основные параметры
        result += f"• Тип объекта: {property_type}\n"
        result += f"• Площадь: {calculation['area']} кв.м\n"
        result += f"• Сложность дизайн-проекта: {design_complexity}\n"
        result += f"• Сложность реализации: {implementation_complexity}\n"
        
        # Информация о проекте
        if calculation['has_project']:
            result += "• Дизайн-проект: уже имеется\n"
        else:
            result += f"• Создание дизайн-проекта: {calculation['project_price']} руб.\n"
        
        # Информация о дополнительных элементах
        if calculation['additional_features']:
            result += "\nДополнительные элементы:\n"
            for feature in calculation['additional_features']:
                feature_name = get_formatted_name(self.ADDITIONAL_FEATURES_NAMES, feature)
                feature_price = calculation['feature_prices'].get(feature, 0)
                result += f"• {feature_name}: {feature_price} руб.\n"
        
        # Стоимость
        result += f"\n• Базовая стоимость реализации: {calculation['base_price']} руб.\n"
        
        if calculation['project_price'] > 0:
            result += f"• Стоимость создания дизайн-проекта: {calculation['project_price']} руб.\n"
        
        if calculation['additional_price'] > 0:
            result += f"• Стоимость дополнительных элементов: {calculation['additional_price']} руб.\n"
        
        result += f"• Общая стоимость: {calculation['total_price']} руб.\n"
        
        # Добавляем важное примечание
        result += "\n⚠️ ВНИМАНИЕ: Это предварительная оценка стоимости работ по дизайн-проекту. "
        result += "Для составления точной сметы необходим выезд специалиста на объект и детальное "
        result += "изучение дизайн-проекта. Окончательная стоимость может отличаться в зависимости "
        result += "от особенностей проекта и дополнительных требований."
        
        return result


# Функции для интеграции с диспетчером калькуляторов

def start_design_calculation(session_id, chat_states, initial_data=None):
    """
    Запускает калькулятор работ по дизайн-проекту
    
    Args:
        session_id (str): Идентификатор сессии
        chat_states (dict): Словарь состояний чата
        initial_data (dict, optional): Начальные данные
        
    Returns:
        str: Первое сообщение калькулятора
    """
    return BaseCalculatorDialog.start_dialog(DesignCalculator, session_id, chat_states, initial_data)

def process_design_calculation(user_input, session_id, chat_states):
    """
    Обрабатывает ввод пользователя в диалоге калькулятора работ по дизайн-проекту
    
    Args:
        user_input (str): Сообщение пользователя
        session_id (str): Идентификатор сессии
        chat_states (dict): Словарь состояний чата
        
    Returns:
        str: Ответ калькулятора
    """
    return BaseCalculatorDialog.process_dialog(DesignCalculator, user_input, session_id, chat_states)