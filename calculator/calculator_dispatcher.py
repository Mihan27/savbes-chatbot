import logging
import re
import traceback  # ← ДОБАВЛЕНО!
from datetime import datetime

# Настройка логгера для dispatcher
dispatcher_logger = logging.getLogger(__name__)

# Импорты калькуляторов с обработкой ошибок
try:
    from calculator.socket_calculator import SocketCalculator, process_socket_calculation
    dispatcher_logger.info("Калькулятор розеток успешно импортирован")
    SOCKET_PROCESS_AVAILABLE = True
except ImportError as e:
    dispatcher_logger.error(f"Ошибка импорта калькулятора розеток: {str(e)}")
    SocketCalculator = None
    process_socket_calculation = None
    SOCKET_PROCESS_AVAILABLE = False

try:
    from calculator.lighting_calculator import LightingCalculator, process_lighting_calculation
    dispatcher_logger.info("Калькулятор освещения успешно импортирован")
    LIGHTING_PROCESS_AVAILABLE = True
except ImportError as e:
    dispatcher_logger.error(f"Ошибка импорта калькулятора освещения: {str(e)}")
    LightingCalculator = None
    process_lighting_calculation = None
    LIGHTING_PROCESS_AVAILABLE = False

try:
    from calculator.panel_calculator import PanelCalculator
    dispatcher_logger.info("Калькулятор электрощитов успешно импортирован")
except ImportError as e:
    dispatcher_logger.error(f"Ошибка импорта калькулятора электрощитов: {str(e)}")
    PanelCalculator = None

try:
    from calculator.cabling_calculator import CablingCalculator
    dispatcher_logger.info("Калькулятор кабельных работ успешно импортирован")
except ImportError as e:
    dispatcher_logger.error(f"Ошибка импорта калькулятора кабельных работ: {str(e)}")
    CablingCalculator = None

try:
    from calculator.base_calculator import BaseCalculator, BaseCalculatorDialog
    dispatcher_logger.info("Базовый калькулятор успешно импортирован")
except ImportError as e:
    dispatcher_logger.error(f"Ошибка импорта базового калькулятора: {str(e)}")
    BaseCalculator = None
    BaseCalculatorDialog = None

try:
    from calculator.multi_service_calculator import MultiServiceCalculator
    dispatcher_logger.info("Многофункциональный калькулятор успешно импортирован")
except ImportError as e:
    dispatcher_logger.error(f"Ошибка импорта многофункционального калькулятора: {str(e)}")
    MultiServiceCalculator = None

try:
    from calculator.standard_calculator import StandardCalculator
    dispatcher_logger.info("Стандартный калькулятор успешно импортирован")
except ImportError as e:
    dispatcher_logger.error(f"Ошибка импорта стандартного калькулятора: {str(e)}")
    StandardCalculator = None


class CalculatorDispatcher:
    
    @staticmethod
    def detect_calculator_type(message):
        """
        Определяет тип калькулятора на основе сообщения пользователя
        """
        message_lower = message.lower()
        
        # Счетчики совпадений
        socket_count = 0
        lighting_count = 0
        panel_count = 0
        cabling_count = 0
        
        # Ключевые слова для розеток и выключателей
        socket_keywords = ["розетк", "выключател", "переключател", "диммер", "usb розетк"]
        for keyword in socket_keywords:
            socket_count += message_lower.count(keyword)
        
        # Ключевые слова для освещения
        lighting_keywords = ["светильник", "свет", "освещени", "лампочк", "люстр", "бра", "спот", "трек"]
        for keyword in lighting_keywords:
            lighting_count += message_lower.count(keyword)
        
        # Ключевые слова для электрощитов
        panel_keywords = ["щит", "электрощит", "автомат", "узо", "счетчик", "дифавтомат", "рубильник"]
        for keyword in panel_keywords:
            panel_count += message_lower.count(keyword)
        
        # Ключевые слова для кабельных работ
        cabling_keywords = ["кабель", "проводк", "провод", "штроб", "канал", "гофр", "трасс"]
        for keyword in cabling_keywords:
            cabling_count += message_lower.count(keyword)
        
        dispatcher_logger.info(f"Совпадения - розетки: {socket_count}, свет: {lighting_count}, щит: {panel_count}, кабель: {cabling_count}")
        
        # Определяем тип калькулятора
        max_count = max(socket_count, lighting_count, panel_count, cabling_count)
        
        if max_count == 0:
            return "standard", False
        
        # Если много разных типов - используем многофункциональный
        non_zero_counts = sum([1 for count in [socket_count, lighting_count, panel_count, cabling_count] if count > 0])
        if non_zero_counts > 1:
            return "multi", True
        
        # Выбираем тип с максимальным количеством совпадений
        if socket_count == max_count:
            return "socket", False
        elif lighting_count == max_count:
            return "lighting", False
        elif panel_count == max_count:
            return "panel", False
        elif cabling_count == max_count:
            return "cabling", False
        
        return "standard", False
    
    @staticmethod
    def detect_calculator_details(message):
        """
        Извлекает детальную информацию из сообщения для калькулятора
        """
        dispatcher_logger.info(f"Извлечение деталей из сообщения: {message}")
        
        # Определяем тип калькулятора
        calculator_type, use_multi = CalculatorDispatcher.detect_calculator_type(message)
        
        # Извлекаем параметры
        extracted_params = {}
        message_lower = message.lower()
        
        # Извлекаем тип объекта
        if any(word in message_lower for word in ["квартир", "комнат"]):
            extracted_params["property_type"] = "apartment"
            dispatcher_logger.info("Автоматически определен тип объекта: apartment")
        elif any(word in message_lower for word in ["дом", "коттедж", "частн"]):
            extracted_params["property_type"] = "house"
            dispatcher_logger.info("Автоматически определен тип объекта: house")
        elif any(word in message_lower for word in ["офис", "кабинет"]):
            extracted_params["property_type"] = "office"
            dispatcher_logger.info("Автоматически определен тип объекта: office")
        
        # Извлекаем площадь
        area_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:кв\.?м|м2|квадрат)', message_lower)
        if area_match:
            try:
                area = float(area_match.group(1).replace(',', '.'))
                extracted_params["area"] = area
                dispatcher_logger.info(f"Автоматически определена площадь: {area} кв.м")
            except ValueError:
                pass
        
        # Извлекаем количество комнат
        rooms_match = re.search(r'(\d+)[\s-]*(?:комнат|комн)', message_lower)
        if rooms_match:
            try:
                rooms = int(rooms_match.group(1))
                extracted_params["rooms"] = rooms
                dispatcher_logger.info(f"Автоматически определено количество комнат: {rooms}")
            except ValueError:
                pass
        
        # Извлекаем материал стен
        if any(word in message_lower for word in ["кирпич", "кирпичн"]):
            extracted_params["wall_material"] = "brick"
            dispatcher_logger.info("Автоматически определен материал стен: brick")
        elif any(word in message_lower for word in ["бетон", "железобетон"]):
            extracted_params["wall_material"] = "concrete"
            dispatcher_logger.info("Автоматически определен материал стен: concrete")
        elif any(word in message_lower for word in ["гипсокартон", "гкл"]):
            extracted_params["wall_material"] = "drywall"
            dispatcher_logger.info("Автоматически определен материал стен: drywall")
        
        dispatcher_logger.info(f"Извлеченные параметры: {extracted_params}")
        dispatcher_logger.info(f"Определен тип калькулятора: {calculator_type}, мульти: {use_multi}")
        
        return calculator_type, use_multi, extracted_params
    
    @staticmethod
    def start_calculation(calculator_type, session_id, chat_states, initial_data=None):
        """
        Запускает расчет с определенным калькулятором
        """
        try:
            dispatcher_logger.info(f"Запуск калькулятора типа '{calculator_type}' для сессии {session_id}")
            dispatcher_logger.info(f"Предварительные данные: {initial_data}")
            
            if calculator_type == "socket":
                dispatcher_logger.info("Используем калькулятор розеток")
                if SocketCalculator is None:
                    return "Извините, калькулятор розеток временно недоступен. Попробуйте позже."
                
                # ✅ ПРАВИЛЬНЫЙ вызов через BaseCalculatorDialog
                if BaseCalculatorDialog:
                    return BaseCalculatorDialog.start_dialog(SocketCalculator, session_id, chat_states, initial_data)
                else:
                    # Запасной вариант - создаем экземпляр калькулятора
                    socket_calc = SocketCalculator()
                    if hasattr(socket_calc, 'start_dialog'):
                        return socket_calc.start_dialog(session_id, chat_states, initial_data)
                    else:
                        return "Выберите тип объекта:\n1. Квартира\n2. Дом/коттедж\n3. Офис"
                    
            elif calculator_type == "lighting":
                dispatcher_logger.info("Используем калькулятор освещения")
                if LightingCalculator is None:
                    return "Извините, калькулятор освещения временно недоступен. Попробуйте позже."
                
                if BaseCalculatorDialog:
                    return BaseCalculatorDialog.start_dialog(LightingCalculator, session_id, chat_states, initial_data)
                else:
                    lighting_calc = LightingCalculator()
                    if hasattr(lighting_calc, 'start_dialog'):
                        return lighting_calc.start_dialog(session_id, chat_states, initial_data)
                    else:
                        return "Выберите тип объекта:\n1. Квартира\n2. Дом/коттедж\n3. Офис"
                    
            elif calculator_type == "panel":
                dispatcher_logger.info("Используем калькулятор электрощитов")
                if PanelCalculator is None:
                    return "Извините, калькулятор электрощитов временно недоступен. Попробуйте позже."
                
                if BaseCalculatorDialog:
                    return BaseCalculatorDialog.start_dialog(PanelCalculator, session_id, chat_states, initial_data)
                else:
                    panel_calc = PanelCalculator()
                    if hasattr(panel_calc, 'start_dialog'):
                        return panel_calc.start_dialog(session_id, chat_states, initial_data)
                    else:
                        return "Выберите тип объекта:\n1. Квартира\n2. Дом/коттедж\n3. Офис"
                    
            elif calculator_type == "cabling":
                dispatcher_logger.info("Используем калькулятор кабельных работ")
                if CablingCalculator is None:
                    return "Извините, калькулятор кабельных работ временно недоступен. Попробуйте позже."
                
                if BaseCalculatorDialog:
                    return BaseCalculatorDialog.start_dialog(CablingCalculator, session_id, chat_states, initial_data)
                else:
                    cabling_calc = CablingCalculator()
                    if hasattr(cabling_calc, 'start_dialog'):
                        return cabling_calc.start_dialog(session_id, chat_states, initial_data)
                    else:
                        return "Выберите тип объекта:\n1. Квартира\n2. Дом/коттедж\n3. Офис"
                    
            elif calculator_type == "multi":
                dispatcher_logger.info("Используем многофункциональный калькулятор")
                if MultiServiceCalculator is None:
                    return "Извините, многофункциональный калькулятор временно недоступен."
                
                # ✅ ИСПРАВЛЕНО: Используем правильный статический метод
                try:
                    return MultiServiceCalculator.start_multi_calculation(session_id, chat_states, initial_data)
                except Exception as e:
                    dispatcher_logger.error(f"Ошибка при запуске многофункционального калькулятора: {str(e)}")
                    return "Выберите тип объекта:\n1. Квартира\n2. Дом/коттедж\n3. Офис"
                    
            elif calculator_type == "standard":
                dispatcher_logger.info("Используем стандартный калькулятор")
                if StandardCalculator is None:
                    return "Извините, стандартный калькулятор временно недоступен."
                
                if BaseCalculatorDialog:
                    return BaseCalculatorDialog.start_dialog(StandardCalculator, session_id, chat_states, initial_data)
                else:
                    try:
                        standard_calc = StandardCalculator()
                        if hasattr(standard_calc, 'start_dialog'):
                            return standard_calc.start_dialog(session_id, chat_states, initial_data)
                        else:
                            return "Выберите тип объекта:\n1. Квартира\n2. Дом/коттедж\n3. Офис"
                    except Exception as e:
                        dispatcher_logger.error(f"Ошибка при запуске стандартного калькулятора: {str(e)}")
                        return "Выберите тип объекта:\n1. Квартира\n2. Дом/коттедж\n3. Офис"
            
            else:
                dispatcher_logger.warning(f"Неизвестный тип калькулятора: {calculator_type}")
                return "Извините, не могу определить тип услуги. Опишите подробнее, что вам нужно?"
                
        except Exception as e:
            dispatcher_logger.error(f"Ошибка при запуске калькулятора: {str(e)}")
            dispatcher_logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Возвращаем понятное сообщение пользователю
            return "Произошла техническая ошибка. Попробуйте переформулировать ваш запрос или обратитесь к специалисту."
    
    @staticmethod
    def process_calculation(calculator_type, user_input, session_id, chat_states):
        """
        Обрабатывает ввод пользователя для активного калькулятора
        
        Args:
            calculator_type (str): Тип калькулятора
            user_input (str): Ввод пользователя
            session_id (str): ID сессии
            chat_states (dict): Состояния чатов
            
        Returns:
            str: Ответ калькулятора
        """
        dispatcher_logger.info(f"Обработка ввода для калькулятора '{calculator_type}', сессия {session_id}")
        
        try:
            # Специальная обработка для socket и lighting калькуляторов
            if calculator_type == "socket" and SOCKET_PROCESS_AVAILABLE:
                return process_socket_calculation(user_input, session_id, chat_states)
            elif calculator_type == "lighting" and LIGHTING_PROCESS_AVAILABLE:
                return process_lighting_calculation(user_input, session_id, chat_states)
            elif calculator_type == "multi" and MultiServiceCalculator:
                # ✅ Используем правильный метод для обработки в multi калькуляторе
                return MultiServiceCalculator.process_multi_calculation(user_input, session_id, chat_states)
            
            # Для остальных калькуляторов используем BaseCalculatorDialog
            calculator_class = None
            
            if calculator_type == "socket" and SocketCalculator and not SOCKET_PROCESS_AVAILABLE:
                calculator_class = SocketCalculator
            elif calculator_type == "lighting" and LightingCalculator and not LIGHTING_PROCESS_AVAILABLE:
                calculator_class = LightingCalculator
            elif calculator_type == "panel" and PanelCalculator:
                calculator_class = PanelCalculator
            elif calculator_type == "cabling" and CablingCalculator:
                calculator_class = CablingCalculator
            elif calculator_type == "standard" and StandardCalculator:
                calculator_class = StandardCalculator
            
            if calculator_class and BaseCalculatorDialog:
                return BaseCalculatorDialog.process_dialog(calculator_class, user_input, session_id, chat_states)
            else:
                dispatcher_logger.warning(f"Обработчик для калькулятора '{calculator_type}' недоступен")
                return "Произошла ошибка. Пожалуйста, начните расчет заново."
                
        except Exception as e:
            dispatcher_logger.error(f"Ошибка при обработке ввода: {str(e)}")
            dispatcher_logger.error(traceback.format_exc())
            return "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз."