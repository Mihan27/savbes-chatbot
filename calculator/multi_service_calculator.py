# calculator/multi_service_calculator.py
# Многофункциональный калькулятор для расчета нескольких услуг одновременно

import logging
import re
import traceback
from datetime import datetime
from .base_calculator import BaseCalculator
from .services_prices import (
    PROPERTY_TYPE_NAMES, get_formatted_name
)

# Создаем логгер для многофункционального калькулятора
multi_logger = logging.getLogger('multi_calculator')
multi_logger.setLevel(logging.DEBUG)

# Импортируем все доступные калькуляторы
try:
    from .lighting_calculator import LightingCalculator
    LIGHTING_CALCULATOR_AVAILABLE = True
    multi_logger.info("Калькулятор освещения успешно импортирован")
except ImportError as e:
    LIGHTING_CALCULATOR_AVAILABLE = False
    multi_logger.error(f"Ошибка импорта калькулятора освещения: {str(e)}")

try:
    from .panel_calculator import PanelCalculator
    PANEL_CALCULATOR_AVAILABLE = True
    multi_logger.info("Калькулятор электрощитов успешно импортирован")
except ImportError as e:
    PANEL_CALCULATOR_AVAILABLE = False
    multi_logger.error(f"Ошибка импорта калькулятора электрощитов: {str(e)}")

try:
    from .socket_calculator import SocketCalculator
    SOCKET_CALCULATOR_AVAILABLE = True
    multi_logger.info("Калькулятор розеток успешно импортирован")
except ImportError as e:
    SOCKET_CALCULATOR_AVAILABLE = False
    multi_logger.error(f"Ошибка импорта калькулятора розеток: {str(e)}")

try:
    from .cabling_calculator import CablingCalculator
    CABLING_CALCULATOR_AVAILABLE = True
    multi_logger.info("Калькулятор кабельных работ успешно импортирован")
except ImportError as e:
    CABLING_CALCULATOR_AVAILABLE = False
    multi_logger.error(f"Ошибка импорта калькулятора кабельных работ: {str(e)}")

# Также импортируем стандартный калькулятор для обратной совместимости
try:
    from .price_calculator import PriceCalculator
    PRICE_CALCULATOR_AVAILABLE = True
    multi_logger.info("Стандартный калькулятор успешно импортирован")
except ImportError as e:
    PRICE_CALCULATOR_AVAILABLE = False
    multi_logger.error(f"Ошибка импорта стандартного калькулятора: {str(e)}")

# Определяем логические связи между услугами
SERVICE_DEPENDENCIES = {
    "socket": {  # Розетки зависят от кабелей и щита
        "required": ["cabling", "panel"],
        "message": "Для установки розеток потребуется прокладка кабелей и подключение к электрощиту."
    },
    "lighting": {  # Освещение зависит от кабелей и щита
        "required": ["cabling", "panel"],
        "message": "Для монтажа освещения потребуется прокладка кабелей и подключение к электрощиту."
    },
    "panel": {  # Щит не имеет явных зависимостей, но рекомендуется заземление
        "required": [],
        "recommended": ["grounding"],
        "message": "Для электрощита рекомендуется также установка системы заземления."
    }
}

# Сервисы, которые обычно нужны для разных типов объектов
TYPICAL_SERVICES = {
    "apartment": ["panel", "socket", "lighting", "cabling"],
    "house": ["panel", "socket", "lighting", "cabling", "grounding"],
    "office": ["panel", "socket", "lighting", "cabling", "network"],
    "commercial": ["panel", "socket", "lighting", "cabling", "security"],
    "industrial": ["panel", "cabling", "industrial_power"]
}

# Типовые количества устройств в зависимости от площади
def get_typical_quantities(property_type, area):
    """Возвращает примерное количество устройств в зависимости от типа помещения и площади"""
    
    # Базовые количества для квартиры площадью 50 кв.м
    base_quantities = {
        "sockets": 10,  # Розетки
        "lights": 5,    # Светильники
        "breakers": 6,  # Автоматы
        "cable_meters": 100  # Метры кабеля
    }
    
    # Коэффициенты для разных типов помещений
    type_multipliers = {
        "apartment": {"sockets": 1.0, "lights": 1.0, "breakers": 1.0, "cable_meters": 1.0},
        "house": {"sockets": 1.2, "lights": 1.3, "breakers": 1.5, "cable_meters": 1.5},
        "office": {"sockets": 1.5, "lights": 1.2, "breakers": 1.3, "cable_meters": 1.3},
        "commercial": {"sockets": 1.3, "lights": 1.5, "breakers": 1.4, "cable_meters": 1.4},
        "industrial": {"sockets": 0.8, "lights": 1.1, "breakers": 1.8, "cable_meters": 1.7}
    }
    
    # Используем коэффициенты по умолчанию, если тип неизвестен
    multiplier = type_multipliers.get(property_type, type_multipliers["apartment"])
    
    # Рассчитываем количество в зависимости от площади и типа помещения
    area_factor = area / 50.0  # Нормализуем к базовой площади
    
    return {
        "sockets": round(base_quantities["sockets"] * multiplier["sockets"] * area_factor),
        "lights": round(base_quantities["lights"] * multiplier["lights"] * area_factor),
        "breakers": round(base_quantities["breakers"] * multiplier["breakers"] * area_factor),
        "cable_meters": round(base_quantities["cable_meters"] * multiplier["cable_meters"] * area_factor)
    }

class MultiServiceCalculator(BaseCalculator):
    """
    Многофункциональный калькулятор для одновременного расчета нескольких услуг
    """
    
    # Переопределяем константы базового класса
    NAME = "Комплексный расчет нескольких услуг"
    TYPE = "multi"
    
    # Доступные сервисы для расчета
    AVAILABLE_SERVICES = {}
    
    if LIGHTING_CALCULATOR_AVAILABLE:
        AVAILABLE_SERVICES["lighting"] = {
            "name": "Монтаж освещения",
            "class": LightingCalculator,
        }
    
    if PANEL_CALCULATOR_AVAILABLE:
        AVAILABLE_SERVICES["panel"] = {
            "name": "Монтаж электрощита",
            "class": PanelCalculator,
        }
    
    if SOCKET_CALCULATOR_AVAILABLE:
        AVAILABLE_SERVICES["socket"] = {
            "name": "Монтаж розеток и выключателей",
            "class": SocketCalculator,
        }
    
    if CABLING_CALCULATOR_AVAILABLE:
        AVAILABLE_SERVICES["cabling"] = {
            "name": "Прокладка кабелей и проводки",
            "class": CablingCalculator,
        }
    
    if PRICE_CALCULATOR_AVAILABLE:
        AVAILABLE_SERVICES["general"] = {
            "name": "Общий электромонтаж",
            "class": None,  # Используем стандартный калькулятор
        }
    
    # Определяем шаги диалога для многофункционального калькулятора
    DIALOG_STEPS = [
        "property_type",         # Тип объекта (общий для всех услуг)
        "area",                  # Площадь (общая для всех услуг)
        "is_new_construction",   # Новостройка или ремонт
        "infrastructure_check",  # Проверка наличия инфраструктуры (кабели, щит)
        "select_services",       # Выбор услуг для расчета
        "service_details",       # Детали для каждой услуги
        "confirmation"           # Подтверждение
    ]
    
    # Определяем сообщения для каждого шага
    STEP_MESSAGES = {
        "property_type": ("Выберите тип объекта для комплексного расчета:\n"
                        "1. Квартира\n"
                        "2. Дом/коттедж\n"
                        "3. Офис\n"
                        "4. Коммерческое помещение\n"
                        "5. Промышленное помещение"),
        
        "area": "Укажите общую площадь помещения в квадратных метрах:",
        
        "is_new_construction": ("Это новая постройка или ремонт существующего помещения?\n"
                              "1. Новостройка / новое помещение\n"
                              "2. Ремонт существующего помещения"),
        
        "infrastructure_check": "Сейчас я задам несколько вопросов о текущем состоянии электрики...",
        
        "has_panel": "У вас уже есть установленный и подключенный электрощит с необходимым количеством автоматов?",
        
        "has_cabling": "Кабели уже проложены к местам установки розеток и светильников?",
        
        "select_services": "Выберите услуги для расчета (введите номера через запятую):"
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
        
        "is_new_construction": {
            "1": True, "новостройка": True, "новая": True, "новое": True,
            "2": False, "ремонт": False, "старое": False, "существующее": False
        },
        
        "has_panel": {
            "да": True, "есть": True, "установлен": True, "имеется": True,
            "нет": False, "отсутствует": False, "не установлен": False, "нужен": False
        },
        
        "has_cabling": {
            "да": True, "есть": True, "проложены": True, "имеются": True,
            "нет": False, "отсутствуют": False, "не проложены": False, "нужны": False
        }
    }
    
    def __init__(self):
        """Инициализация калькулятора"""
        # Создаем экземпляры отдельных калькуляторов
        self.calculators = {}
        
        if LIGHTING_CALCULATOR_AVAILABLE:
            self.calculators["lighting"] = LightingCalculator()
        
        if PANEL_CALCULATOR_AVAILABLE:
            self.calculators["panel"] = PanelCalculator()
            
        if SOCKET_CALCULATOR_AVAILABLE:
            self.calculators["socket"] = SocketCalculator()
            
        if CABLING_CALCULATOR_AVAILABLE:
            self.calculators["cabling"] = CablingCalculator()
        
        # Стандартный калькулятор добавляем отдельно, если доступен
        self.price_calculator_available = PRICE_CALCULATOR_AVAILABLE
    
    def calculate(self, data):
        """
        Рассчитывает стоимость всех выбранных услуг
        
        Args:
            data (dict): Данные для расчета
            
        Returns:
            dict: Результат расчета
        """
        # Логируем начало расчета
        multi_logger.info(f"Начат комплексный расчет с данными: {data}")
        
        try:
            # Получаем необходимые параметры из данных
            property_type = data.get("property_type", "apartment")
            area = data.get("area", 0)
            selected_services = data.get("selected_services", [])
            service_data = data.get("service_data", {})
            
            # Проверяем наличие выбранных услуг
            if not selected_services:
                error_msg = "Не выбрано ни одной услуги для расчета"
                multi_logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Результаты расчетов по каждой услуге
            service_results = {}
            total_price = 0
            
            # Рассчитываем каждую выбранную услугу
            for service_type in selected_services:
                multi_logger.info(f"Расчет для услуги: {service_type}")
                
                # Формируем данные для расчета этой услуги
                service_input = {
                    "property_type": property_type,
                    "area": area
                }
                
                # Добавляем специфичные для услуги данные
                if service_type in service_data:
                    service_input.update(service_data[service_type])
                    multi_logger.info(f"Добавлены специфичные данные для {service_type}: {service_data[service_type]}")
                
                # Проверяем тип услуги
                if service_type == "general" and self.price_calculator_available:
                    multi_logger.info("Используем стандартный kalькулятор для общего электромонтажа")
                    
                    # Используем стандартный калькулятор
                    basic_calc = PriceCalculator.calculate_basic_price(
                        property_type=property_type,
                        area=area,
                        wall_material=service_input.get("wall_material", "brick"),
                        num_rooms=service_input.get("num_rooms", 1)
                    )
                    
                    # Добавляем дополнительные услуги
                    additional_services = service_input.get("additional_services", [])
                    if additional_services:
                        result = PriceCalculator.add_services(basic_calc, additional_services)
                    else:
                        result = basic_calc
                    
                    # Форматируем результат
                    formatted_result = PriceCalculator.format_calculation_result(result)
                    
                    # Сохраняем результат
                    service_results[service_type] = {
                        "price": result["price"],
                        "formatted": formatted_result,
                        "details": result
                    }
                    
                    # Добавляем к общей стоимости
                    total_price += result["price"]
                    multi_logger.info(f"Стоимость общего электромонтажа: {result['price']} руб.")
                    
                elif service_type in self.calculators:
                    multi_logger.info(f"Используем специализированный калькулятор для {service_type}")
                    
                    # Используем специализированный калькулятор
                    calculator = self.calculators[service_type]
                    try:
                        result = calculator.calculate(service_input)
                        formatted_result = calculator.format_result(result)
                        
                        # Сохраняем результат
                        service_results[service_type] = {
                            "price": result["price"],
                            "formatted": formatted_result,
                            "details": result
                        }
                        
                        # Добавляем к общей стоимости
                        total_price += result["price"]
                        multi_logger.info(f"Стоимость {service_type}: {result['price']} руб.")
                        
                    except Exception as e:
                        multi_logger.error(f"Ошибка при расчете услуги {service_type}: {str(e)}")
                        service_results[service_type] = {
                            "error": str(e),
                            "price": 0,
                            "formatted": f"Ошибка при расчете: {str(e)}"
                        }
                else:
                    # Неизвестный тип услуги
                    multi_logger.warning(f"Неизвестный тип услуги: {service_type}")
                    service_results[service_type] = {
                        "error": "Услуга не поддерживается",
                        "price": 0,
                        "formatted": "Ошибка: тип услуги не поддерживается"
                    }
            
            # Формируем общий результат
            result = {
                "property_type": property_type,
                "area": area,
                "selected_services": selected_services,
                "service_results": service_results,
                "total_price": total_price,
                "price": total_price  # Для совместимости с другими калькуляторами
            }
            
            multi_logger.info(f"Комплексный расчет завершен. Итоговая стоимость: {total_price} руб.")
            
            return result
            
        except Exception as e:
            multi_logger.error(f"Критическая ошибка при комплексном расчете: {str(e)}")
            multi_logger.error(traceback.format_exc())
            
            # Возвращаем базовый результат в случае ошибки
            return {
                "property_type": data.get("property_type", "apartment"),
                "area": data.get("area", 0),
                "selected_services": [],
                "service_results": {},
                "total_price": 0,
                "price": 0
            }
    
    def format_result(self, calculation):
        """
        Форматирует результат расчета в читаемый текст
        
        Args:
            calculation (dict): Результат расчета
            
        Returns:
            str: Форматированный текст
        """
        multi_logger.info("Форматирование результатов комплексного расчета")
        
        try:
            # Форматируем текст результата
            result = "📋 Комплексный расчет стоимости электромонтажных работ:\n\n"
            
            # Общие параметры
            property_type = get_formatted_name(PROPERTY_TYPE_NAMES, calculation['property_type'])
            result += f"• Тип объекта: {property_type}\n"
            result += f"• Площадь помещения: {calculation['area']} кв.м\n\n"
            
            # Результаты по отдельным услугам
            result += "Расчет по выбранным услугам:\n"
            
            service_names = {
                "general": "Общий электромонтаж",
                "lighting": "Монтаж освещения",
                "panel": "Монтаж электрощита",
                "socket": "Монтаж розеток и выключателей",
                "cabling": "Прокладка кабелей и проводки"
            }
            
            for service_type in calculation['selected_services']:
                service_name = service_names.get(service_type, service_type)
                
                if service_type in calculation['service_results']:
                    service_result = calculation['service_results'][service_type]
                    
                    if "error" in service_result:
                        result += f"\n🔴 {service_name}: Ошибка расчета\n"
                        result += f"    {service_result['error']}\n"
                    else:
                        result += f"\n🔹 {service_name}: {service_result['price']} руб.\n"
                else:
                    result += f"\n🔴 {service_name}: Результат недоступен\n"
            
            # Общая стоимость
            result += f"\n💰 Общая стоимость всех работ: {calculation['total_price']} руб.\n"
            
            # Добавляем важное примечание
            result += "\n⚠️ ВНИМАНИЕ: Это предварительная оценка. Точная стоимость определяется "
            result += "только после выезда специалиста и составления детальной сметы. "
            result += "Окончательная цена может отличаться в зависимости от особенностей объекта."
            
            multi_logger.info("Форматирование результатов завершено")
            
            return result
            
        except Exception as e:
            multi_logger.error(f"Ошибка при форматировании результатов: {str(e)}")
            multi_logger.error(traceback.format_exc())
            
            # В случае ошибки возвращаем простой результат
            return f"Результат комплексного расчета: {calculation.get('total_price', 0)} руб.\n\nПожалуйста, обратитесь к менеджеру для получения детальной информации."
    
    def check_service_dependencies(self, selected_services):
        """
        Проверяет зависимости между услугами и предлагает дополнительные
        
        Args:
            selected_services (list): Список выбранных услуг
            
        Returns:
            dict: Информация о зависимостях и рекомендациях
        """
        multi_logger.info(f"Проверка зависимостей для услуг: {selected_services}")
        
        dependencies = {
            "required": [],
            "recommended": [],
            "messages": []
        }
        
        for service in selected_services:
            if service in SERVICE_DEPENDENCIES:
                service_deps = SERVICE_DEPENDENCIES[service]
                
                # Проверяем обязательные зависимости
                for required in service_deps.get("required", []):
                    if required not in selected_services and required not in dependencies["required"]:
                        dependencies["required"].append(required)
                        multi_logger.info(f"Найдена обязательная зависимость: {required} для {service}")
                
                # Проверяем рекомендованные зависимости
                for recommended in service_deps.get("recommended", []):
                    if recommended not in selected_services and recommended not in dependencies["recommended"]:
                        dependencies["recommended"].append(recommended)
                        multi_logger.info(f"Найдена рекомендуемая зависимость: {recommended} для {service}")
                
                # Добавляем сообщение
                if service_deps.get("message"):
                    dependencies["messages"].append(service_deps["message"])
        
        return dependencies
    
    def get_service_selection_message(self, property_type, area, initial_data=None):
        """
        Формирует сообщение для выбора услуг с учетом типичных потребностей
        
        Args:
            property_type (str): Тип помещения
            area (float): Площадь помещения
            initial_data (dict): Предварительные данные из запроса
            
        Returns:
            str: Сообщение для выбора услуг
        """
        multi_logger.info(f"Формирование сообщения выбора услуг для {property_type}, площадь {area}")
        
        # Получаем типичные количества
        typical = get_typical_quantities(property_type, area)
        
        # Формируем сообщение
        property_name = get_formatted_name(PROPERTY_TYPE_NAMES, property_type)
        
        message = f"📏 Для объекта '{property_name}' площадью {area} кв.м обычно требуется:\n\n"
        
        message += f"• Электрощит с {typical['breakers']} автоматами\n"
        message += f"• Прокладка около {typical['cable_meters']} метров кабеля\n"
        message += f"• Установка около {typical['sockets']} розеток\n"
        message += f"• Монтаж около {typical['lights']} светильников\n\n"
        
        message += "🔧 Выберите услуги для расчета (введите номера через запятую):\n\n"
        
        # Добавляем доступные услуги
        service_counter = 1
        for service_key, service_info in self.AVAILABLE_SERVICES.items():
            message += f"{service_counter}. {service_info['name']}\n"
            service_counter += 1
        
        message += f"\n{service_counter}. Все услуги (комплексный расчет)\n"
        
        return message
    
    def parse_service_selection(self, user_input):
        """
        Обрабатывает выбор услуг пользователем
        
        Args:
            user_input (str): Ввод пользователя
            
        Returns:
            list: Список выбранных услуг
        """
        multi_logger.info(f"Обработка выбора услуг: {user_input}")
        
        selected_services = []
        service_list = list(self.AVAILABLE_SERVICES.keys())
        
        # Ищем числа в вводе пользователя
        numbers = re.findall(r'\d+', user_input)
        
        for num_str in numbers:
            try:
                num = int(num_str)
                
                # Проверяем, что номер в допустимом диапазоне
                if 1 <= num <= len(service_list):
                    service_key = service_list[num - 1]
                    if service_key not in selected_services:
                        selected_services.append(service_key)
                        multi_logger.info(f"Выбрана услуга: {service_key}")
                elif num == len(service_list) + 1:
                    # Выбраны все услуги
                    selected_services = service_list.copy()
                    multi_logger.info("Выбраны все услуги")
                    break
                    
            except ValueError:
                multi_logger.warning(f"Не удалось обработать номер: {num_str}")
        
        # Если ничего не выбрано, пытаемся найти ключевые слова
        if not selected_services:
            user_input_lower = user_input.lower()
            
            if any(word in user_input_lower for word in ["все", "всё", "комплекс", "полный"]):
                selected_services = service_list.copy()
                multi_logger.info("Выбраны все услуги по ключевым словам")
            elif "розетк" in user_input_lower:
                selected_services.append("socket")
            elif any(word in user_input_lower for word in ["свет", "освещен", "светильник"]):
                selected_services.append("lighting")
            elif any(word in user_input_lower for word in ["щит", "электрощит"]):
                selected_services.append("panel")
            elif any(word in user_input_lower for word in ["кабел", "проводк", "провод"]):
                selected_services.append("cabling")
        
        multi_logger.info(f"Итоговый выбор услуг: {selected_services}")
        return selected_services
    
    def get_service_details_message(self, service_type, property_type, area):
        """
        Формирует сообщение для сбора деталей по конкретной услуге
        
        Args:
            service_type (str): Тип услуги
            property_type (str): Тип помещения
            area (float): Площадь
            
        Returns:
            str: Сообщение для сбора деталей
        """
        multi_logger.info(f"Формирование сообщения для деталей услуги: {service_type}")
        
        service_name = self.AVAILABLE_SERVICES.get(service_type, {}).get("name", service_type)
        
        if service_type == "socket":
            return (f"🔌 Детали для услуги '{service_name}':\n\n"
                   f"Укажите количество точек (розеток, выключателей) или нажмите Enter для автоматического расчета:")
        
        elif service_type == "lighting":
            return (f"💡 Детали для услуги '{service_name}':\n\n"
                   f"Укажите количество светильников или нажмите Enter для автоматического расчета:")
        
        elif service_type == "panel":
            return (f"⚡ Детали для услуги '{service_name}':\n\n"
                   f"Укажите требуемое количество автоматов в щите или нажмите Enter для автоматического расчета:")
        
        elif service_type == "cabling":
            return (f"🔗 Детали для услуги '{service_name}':\n\n"
                   f"Укажите примерную длину кабелей в метрах или нажмите Enter для автоматического расчета:")
        
        else:
            return f"Детали для услуги '{service_name}' будут рассчитаны автоматически. Нажмите Enter для продолжения."
    
    @classmethod
    def match_user_input(cls, step, user_input):
        """
        Сопоставляет ввод пользователя с ожидаемыми значениями
        Переопределяем для совместимости с BaseCalculator
        """
        multi_logger.info(f"match_user_input вызван: шаг={step}, ввод='{user_input}'")
        
        # Используем базовую реализацию для стандартных шагов
        if step in cls.USER_INPUT_MAPPINGS:
            mappings = cls.USER_INPUT_MAPPINGS[step]
            
            # Проверяем прямые совпадения
            for key, value in mappings.items():
                if key in user_input.lower():
                    multi_logger.info(f"Найдено совпадение для {step}: {key} -> {value}")
                    return value, True
            
            multi_logger.warning(f"Нет совпадений для {step}, ввод='{user_input}'")
            return None, False
        
        # Для неизвестных шагов возвращаем ввод как есть
        return user_input, True

    @classmethod
    def extract_known_parameters(cls, initial_data):
        """
        Извлекает известные параметры из начальных данных
        Переопределяем для совместимости с BaseCalculator
        """
        if not initial_data:
            return {}
            
        multi_logger.info(f"Извлечение известных параметров из: {initial_data}")
        
        known_params = {}
        
        # Сопоставляем параметры с шагами диалога
        if "property_type" in initial_data and "property_type" in cls.DIALOG_STEPS:
            known_params["property_type"] = initial_data["property_type"]
            
        if "area" in initial_data and "area" in cls.DIALOG_STEPS:
            known_params["area"] = initial_data["area"]
        
        multi_logger.info(f"Извлеченные известные параметры: {known_params}")
        return known_params
    
    def process_response(self, user_input, session_id, chat_states):
        """
        Обработчик ответов для совместимости с app.py
        
        Args:
            user_input (str): Ввод пользователя
            session_id (str): ID сессии
            chat_states (dict): Состояния чатов
            
        Returns:
            str: Ответ пользователю
        """
        return MultiServiceCalculator.process_multi_calculation(user_input, session_id, chat_states)
    
    @staticmethod
    def start_multi_calculation(session_id, chat_states, initial_data=None):
        """
        Начинает диалог многофункционального калькулятора
        
        Args:
            session_id (str): ID сессии
            chat_states (dict): Состояния чатов
            initial_data (dict): Предварительно извлеченные данные
            
        Returns:
            str: Первое сообщение диалога
        """
        multi_logger.info(f"Запуск многофункционального калькулятора для сессии {session_id}")
        multi_logger.info(f"Предварительные данные: {initial_data}")
        
        # Инициализируем состояние
        chat_states[session_id] = {
            "calculator_type": "multi",  # ✅ ИСПРАВЛЕНО: было "calculator"
            "stage": "property_type",
            "data": initial_data or {},
            "current_service": None,
            "service_details_collected": [],
            "calculation_result": None
        }
        
        # Проверяем, есть ли уже информация о типе объекта
        if initial_data and "property_type" in initial_data:
            property_type = initial_data["property_type"]
            chat_states[session_id]["data"]["property_type"] = property_type
            multi_logger.info(f"Тип объекта уже известен: {property_type}")
            
            # Переходим к следующему шагу
            if "area" in initial_data:
                area = initial_data["area"]
                chat_states[session_id]["data"]["area"] = area
                chat_states[session_id]["stage"] = "is_new_construction"
                multi_logger.info(f"Площадь уже известна: {area}")
                
                property_name = get_formatted_name(PROPERTY_TYPE_NAMES, property_type)
                return (f"✅ Определено: {property_name}, площадь {area} кв.м\n\n"
                       f"{MultiServiceCalculator.STEP_MESSAGES['is_new_construction']}")
            else:
                chat_states[session_id]["stage"] = "area"
                property_name = get_formatted_name(PROPERTY_TYPE_NAMES, property_type)
                return f"✅ Определен тип объекта: {property_name}\n\n{MultiServiceCalculator.STEP_MESSAGES['area']}"
        
        # Стандартное начало диалога
        return MultiServiceCalculator.STEP_MESSAGES["property_type"]
    
    @staticmethod
    def process_multi_calculation(user_input, session_id, chat_states):
        """
        Обрабатывает этапы диалога многофункционального калькулятора
        
        Args:
            user_input (str): Ввод пользователя
            session_id (str): ID сессии
            chat_states (dict): Состояния чатов
            
        Returns:
            str: Ответ пользователю
        """
        multi_logger.info(f"Обработка этапа диалога многофункционального калькулятора")
        multi_logger.info(f"Сессия: {session_id}, этап: {chat_states[session_id].get('stage')}")
        multi_logger.info(f"Ввод пользователя: {user_input}")
        
        try:
            stage = chat_states[session_id]["stage"]
            data = chat_states[session_id]["data"]
            calculator = MultiServiceCalculator()
            
            if stage == "property_type":
                # Обработка выбора типа объекта
                property_type = None
                user_input_lower = user_input.lower().strip()
                
                # Проверяем по маппингу
                for key, value in MultiServiceCalculator.USER_INPUT_MAPPINGS["property_type"].items():
                    if key in user_input_lower:
                        property_type = value
                        break
                
                if not property_type:
                    return "❌ Пожалуйста, выберите тип объекта (1-5) или укажите словами."
                
                data["property_type"] = property_type
                chat_states[session_id]["stage"] = "area"
                
                property_name = get_formatted_name(PROPERTY_TYPE_NAMES, property_type)
                return f"✅ Выбран тип объекта: {property_name}\n\n{MultiServiceCalculator.STEP_MESSAGES['area']}"
            
            elif stage == "area":
                # Обработка ввода площади
                try:
                    area = float(re.search(r'(\d+(?:\.\d+)?)', user_input).group(1))
                    if area <= 0:
                        return "❌ Площадь должна быть больше нуля. Пожалуйста, укажите корректную площадь."
                    
                    data["area"] = area
                    chat_states[session_id]["stage"] = "is_new_construction"
                    
                    return f"✅ Площадь: {area} кв.м\n\n{MultiServiceCalculator.STEP_MESSAGES['is_new_construction']}"
                    
                except (AttributeError, ValueError):
                    return "❌ Пожалуйста, укажите площадь числом (например: 50 или 75.5)."
            
            elif stage == "is_new_construction":
                # Обработка вопроса о новостройке/ремонте
                user_input_lower = user_input.lower().strip()
                is_new = None
                
                for key, value in MultiServiceCalculator.USER_INPUT_MAPPINGS["is_new_construction"].items():
                    if key in user_input_lower:
                        is_new = value
                        break
                
                if is_new is None:
                    return "❌ Пожалуйста, укажите: это новостройка (1) или ремонт существующего помещения (2)?"
                
                data["is_new_construction"] = is_new
                chat_states[session_id]["stage"] = "infrastructure_check"
                
                construction_type = "новостройка" if is_new else "ремонт существующего помещения"
                return f"✅ Тип работ: {construction_type}\n\n{MultiServiceCalculator.STEP_MESSAGES['infrastructure_check']}\n\n{MultiServiceCalculator.STEP_MESSAGES['has_panel']}"
            
            elif stage == "infrastructure_check":
                # Проверка наличия электрощита
                user_input_lower = user_input.lower().strip()
                has_panel = None
                
                for key, value in MultiServiceCalculator.USER_INPUT_MAPPINGS["has_panel"].items():
                    if key in user_input_lower:
                        has_panel = value
                        break
                
                if has_panel is None:
                    return "❌ Пожалуйста, ответьте: есть ли у вас электрощит? (да/нет)"
                
                data["has_panel"] = has_panel
                chat_states[session_id]["stage"] = "has_cabling"
                
                panel_status = "есть" if has_panel else "нужен"
                return f"✅ Электрощит: {panel_status}\n\n{MultiServiceCalculator.STEP_MESSAGES['has_cabling']}"
            
            elif stage == "has_cabling":
                # Проверка наличия кабелей
                user_input_lower = user_input.lower().strip()
                has_cabling = None
                
                for key, value in MultiServiceCalculator.USER_INPUT_MAPPINGS["has_cabling"].items():
                    if key in user_input_lower:
                        has_cabling = value
                        break
                
                if has_cabling is None:
                    return "❌ Пожалуйста, ответьте: проложены ли кабели? (да/нет)"
                
                data["has_cabling"] = has_cabling
                chat_states[session_id]["stage"] = "select_services"
                
                # Формируем сообщение для выбора услуг
                property_type = data["property_type"]
                area = data["area"]
                
                return calculator.get_service_selection_message(property_type, area, data)
            
            elif stage == "select_services":
                # Обработка выбора услуг
                selected_services = calculator.parse_service_selection(user_input)
                
                if not selected_services:
                    return "❌ Пожалуйста, выберите хотя бы одну услугу (укажите номера через запятую)."
                
                data["selected_services"] = selected_services
                
                # Проверяем зависимости
                dependencies = calculator.check_service_dependencies(selected_services)
                
                # Добавляем обязательные зависимости
                for required in dependencies["required"]:
                    if required not in selected_services and required in calculator.AVAILABLE_SERVICES:
                        selected_services.append(required)
                        multi_logger.info(f"Добавлена обязательная зависимость: {required}")
                
                data["selected_services"] = selected_services
                chat_states[session_id]["stage"] = "service_details"
                chat_states[session_id]["current_service"] = 0
                chat_states[session_id]["service_data"] = {}
                
                # Сообщаем о выбранных услугах
                service_names = [calculator.AVAILABLE_SERVICES[s]["name"] for s in selected_services if s in calculator.AVAILABLE_SERVICES]
                
                result = f"✅ Выбранные услуги:\n"
                for name in service_names:
                    result += f"• {name}\n"
                
                if dependencies["messages"]:
                    result += f"\n💡 Информация:\n"
                    for msg in dependencies["messages"]:
                        result += f"• {msg}\n"
                
                # Переходим к сбору деталей первой услуги
                first_service = selected_services[0]
                result += f"\n{calculator.get_service_details_message(first_service, data['property_type'], data['area'])}"
                
                return result
            
            elif stage == "service_details":
                # Сбор деталей по услугам
                selected_services = data["selected_services"]
                current_service_index = chat_states[session_id]["current_service"]
                
                if current_service_index >= len(selected_services):
                    # Все детали собраны, выполняем расчет
                    chat_states[session_id]["stage"] = "completed"
                    
                    # Выполняем расчет
                    calculation = calculator.calculate(data)
                    result = calculator.format_result(calculation)
                    
                    # Сохраняем результат
                    chat_states[session_id]["calculation_result"] = result
                    chat_states[session_id]["full_calc"] = calculation
                    
                    return result + "\n\n🤝 Хотите оставить контактные данные для связи с нашим менеджером? Пожалуйста, укажите имя, телефон и email.[SHOW_CONTACT_FORM]"
                
                # Обрабатываем детали текущей услуги
                current_service = selected_services[current_service_index]
                
                # Сохраняем данные для текущей услуги
                if "service_data" not in data:
                    data["service_data"] = {}
                
                if current_service not in data["service_data"]:
                    data["service_data"][current_service] = {}
                
                # Обрабатываем ввод пользователя для деталей
                if user_input.strip():
                    # Пытаемся извлечь числовое значение
                    try:
                        value = float(re.search(r'(\d+(?:\.\d+)?)', user_input).group(1))
                        
                        if current_service == "socket":
                            data["service_data"][current_service]["points"] = int(value)
                        elif current_service == "lighting":
                            data["service_data"][current_service]["lights_count"] = int(value)
                        elif current_service == "panel":
                            data["service_data"][current_service]["breakers_count"] = int(value)
                        elif current_service == "cabling":
                            data["service_data"][current_service]["cable_length"] = value
                        
                        multi_logger.info(f"Сохранены детали для {current_service}: {value}")
                        
                    except (AttributeError, ValueError):
                        multi_logger.info(f"Не удалось извлечь число из ввода: {user_input}")
                        # Продолжаем с автоматическим расчетом
                
                # Переходим к следующей услуге
                chat_states[session_id]["current_service"] += 1
                next_service_index = chat_states[session_id]["current_service"]
                
                if next_service_index < len(selected_services):
                    next_service = selected_services[next_service_index]
                    return calculator.get_service_details_message(next_service, data["property_type"], data["area"])
                else:
                    # Все детали собраны, выполняем расчет
                    chat_states[session_id]["stage"] = "completed"
                    
                    calculation = calculator.calculate(data)
                    result = calculator.format_result(calculation)
                    
                    chat_states[session_id]["calculation_result"] = result
                    chat_states[session_id]["full_calc"] = calculation
                    
                    return result + "\n\n🤝 Хотите оставить контактные данные для связи с нашим менеджером? Пожалуйста, укажите имя, телефон и email.[SHOW_CONTACT_FORM]"
            
            elif stage == "completed":
                # Калькулятор завершен, обрабатываем контактные данные
                multi_logger.info(f"Обработка контактных данных для завершенного расчета")
                
                # Проверяем, есть ли контактные данные в вводе
                phone_match = re.search(r'(\+7|8)?[\s\-]?\(?(\d{3})\)?[\s\-]?(\d{3})[\s\-]?(\d{2})[\s\-]?(\d{2})', user_input)
                
                if phone_match:
                    phone = phone_match.group(0)
                    
                    # Пытаемся извлечь email
                    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', user_input)
                    email = email_match.group(0) if email_match else None
                    
                    # Остальное считаем именем
                    name = user_input
                    if phone:
                        name = name.replace(phone, '').strip()
                    if email:
                        name = name.replace(email, '').strip()
                    name = name.strip(',').strip()
                    
                    multi_logger.info(f"Извлечены контактные данные: имя={name}, телефон={phone}, email={email}")
                    
                    # Сохраняем контактные данные
                    chat_states[session_id]["contact_data"] = {
                        "name": name,
                        "phone": phone,
                        "email": email
                    }
                    
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
                            
                            # Получаем результат расчета
                            full_calc = chat_states[session_id].get("full_calc", {})
                            
                            success = email_sender.send_client_request(
                                phone_number=phone,
                                dialog_history=dialog_history,
                                calculation_results=full_calc,
                                name=name,
                                email=email
                            )
                            
                            if success:
                                multi_logger.info("Заявка успешно отправлена")
                            else:
                                multi_logger.error("Ошибка при отправке заявки")
                    except Exception as e:
                        multi_logger.error(f"Ошибка при отправке email: {str(e)}")
                    
                    # ВАЖНО: Удаляем состояние калькулятора, чтобы завершить диалог
                    del chat_states[session_id]
                    
                    # Возвращаем благодарность
                    return (f"Спасибо! Ваша заявка принята. Наш специалист свяжется с вами по телефону {phone} "
                           "в ближайшее время для уточнения деталей и согласования времени выезда.\n\n"
                           "Чем еще я могу вам помочь?")
                else:
                    # Если не удалось извлечь телефон, но есть расчет - показываем форму
                    if "calculation_result" in chat_states[session_id]:
                        return (chat_states[session_id]["calculation_result"] + 
                               "\n\n🤝 Хотите оставить контактные данные для связи с нашим менеджером? "
                               "Пожалуйста, укажите имя, телефон и email.[SHOW_CONTACT_FORM]")
                    else:
                        return "Пожалуйста, укажите номер телефона для связи. Например: +7 922 825 8279"
            
            else:
                multi_logger.warning(f"Неизвестный этап диалога: {stage}")
                return "❌ Произошла ошибка в диалоге. Попробуйте начать расчет заново."
        
        except Exception as e:
            multi_logger.error(f"Ошибка при обработке диалога: {str(e)}")
            multi_logger.error(traceback.format_exc())
            return "❌ Произошла ошибка при обработке вашего запроса. Попробуйте еще раз."


# Функции-обертки для интеграции с диспетчером

def start_multi_calculation_wrapper(session_id, chat_states, initial_data=None):
    """
    Обёртка для запуска multi калькулятора через диспетчер
    """
    try:
        return MultiServiceCalculator.start_multi_calculation(session_id, chat_states, initial_data)
    except Exception as e:
        multi_logger.error(f"Ошибка при запуске multi калькулятора: {str(e)}")
        return "К сожалению, произошла ошибка при запуске калькулятора. Пожалуйста, попробуйте еще раз."

def process_multi_calculation_wrapper(user_input, session_id, chat_states):
    """
    Обёртка для обработки ввода в multi калькуляторе через диспетчер
    """
    try:
        return MultiServiceCalculator.process_multi_calculation(user_input, session_id, chat_states)
    except Exception as e:
        multi_logger.error(f"Ошибка при обработке ввода в multi калькуляторе: {str(e)}")
        return "К сожалению, произошла ошибка. Пожалуйста, попробуйте еще раз."