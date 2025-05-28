# base_calculator.py
import logging
import traceback
from abc import ABC, abstractmethod

# Настройка логирования для base_calculator  
base_logger = logging.getLogger('base_calculator')
base_logger.setLevel(logging.DEBUG)

# Проверяем, есть ли уже обработчики
if not base_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    base_logger.addHandler(handler)

# Импортируем глобальные переменные из app.py
try:
    from app import chat_states, chat_history
    base_logger.info("Успешно импортированы chat_states и chat_history из app.py")
except ImportError:
    base_logger.warning("Не удалось импортировать chat_states и chat_history из app.py")
    chat_states = {}
    chat_history = {}

class BaseCalculator(ABC):
    """
    Абстрактный базовый класс для всех калькуляторов
    """
    
    NAME = "Базовый калькулятор"
    TYPE = "base"
    
    @abstractmethod
    def calculate(self, data):
        """Выполняет расчет на основе переданных данных"""
        pass
    
    @abstractmethod
    def format_result(self, calculation):
        """Форматирует результат расчета для отображения пользователю"""
        pass
    
    @classmethod
    def match_user_input(cls, step, user_input):
        """
        Парсит ввод пользователя для конкретного шага
        Возвращает (значение, успех)
        """
        try:
            base_logger.debug(f"match_user_input вызван: шаг={step}, ввод='{user_input}'")
            
            # Базовая логика для числовых значений
            if step in ['socket_singles', 'socket_doubles', 'socket_power', 
                       'switch_singles', 'switch_doubles', 'lights_count']:
                try:
                    value = int(user_input.strip())
                    base_logger.debug(f"Распознано количество для {step}: {value}")
                    return value, True
                except ValueError:
                    base_logger.warning(f"Не удалось распознать число в '{user_input}'")
                    return None, False
            
            # Для выбора из списка (property_type, wall_material, etc.)
            elif step == 'property_type':
                property_mapping = {
                    '1': 'apartment',
                    '2': 'house', 
                    '3': 'office',
                    '4': 'commercial',
                    '5': 'industrial'
                }
                if user_input in property_mapping:
                    result = property_mapping[user_input]
                    base_logger.debug(f"Найдено совпадение для property_type: {user_input} -> {result}")
                    return result, True
                    
            elif step == 'wall_material':
                wall_mapping = {
                    '1': 'drywall',
                    '2': 'brick',
                    '3': 'concrete', 
                    '4': 'wood',
                    '5': 'block'
                }
                if user_input in wall_mapping:
                    result = wall_mapping[user_input]
                    base_logger.debug(f"Найдено совпадение для wall_material: {user_input} -> {result}")
                    return result, True
                    
            elif step == 'complexity':
                complexity_mapping = {
                    '1': 'simple',
                    '2': 'standard',
                    '3': 'complex'
                }
                if user_input in complexity_mapping:
                    result = complexity_mapping[user_input]
                    base_logger.debug(f"Найдено совпадение для complexity: {user_input} -> {result}")
                    return result, True
                    
            base_logger.warning(f"Не найдено совпадение для шага {step} и ввода '{user_input}'")
            return None, False
            
        except Exception as e:
            base_logger.error(f"Ошибка в match_user_input: {str(e)}")
            base_logger.error(f"Traceback: {traceback.format_exc()}")
            return None, False


class BaseCalculatorDialog:
    """
    Класс для управления диалогами с калькуляторами
    """
    
    @staticmethod
    def start_dialog(calculator_class, session_id, chat_states, initial_data=None):
        """
        Начинает диалог с калькулятором
        """
        try:
            base_logger.info(f"Запуск диалога '{calculator_class.NAME}' для сессии {session_id}")
            base_logger.debug(f"Начальные данные: {initial_data}")
            
            # Инициализация состояния диалога
            chat_states[session_id] = {
                "calculator_type": calculator_class.TYPE,  
                "stage": "",
                "data": initial_data or {},
                "next_stages": list(calculator_class.DIALOG_STEPS)
            }
            
            # Извлекаем известные параметры
            known_params = {}
            if hasattr(calculator_class, 'extract_known_parameters'):
                known_params = calculator_class.extract_known_parameters(initial_data or {})
                base_logger.debug(f"Известные параметры через метод класса: {known_params}")
            else:
                # Базовая обработка если метод не определен
                if initial_data:
                    # Простое сопоставление общих параметров
                    if "property_type" in initial_data and hasattr(calculator_class, 'DIALOG_STEPS') and "property_type" in calculator_class.DIALOG_STEPS:
                        known_params["property_type"] = initial_data["property_type"]
                    if "area" in initial_data and hasattr(calculator_class, 'DIALOG_STEPS') and "area" in calculator_class.DIALOG_STEPS:
                        known_params["area"] = initial_data["area"]
                    if "wall_material" in initial_data and hasattr(calculator_class, 'DIALOG_STEPS') and "wall_material" in calculator_class.DIALOG_STEPS:
                        known_params["wall_material"] = initial_data["wall_material"]
                    base_logger.debug(f"Известные параметры через базовую обработку: {known_params}")
                else:
                    base_logger.debug("Нет начальных данных для извлечения параметров")
            
            # Обновляем данные известными параметрами
            chat_states[session_id]["data"].update(known_params)
            
            # Находим первый неизвестный шаг
            for step in calculator_class.DIALOG_STEPS:
                if step not in chat_states[session_id]["data"]:
                    chat_states[session_id]["stage"] = step
                    message = calculator_class.STEP_MESSAGES.get(step, f"Шаг {step}")
                    base_logger.info(f"Возвращаем сообщение для шага '{step}'")
                    return message
                    
            # Если все шаги известны, переходим к расчету
            base_logger.info("Все данные уже известны, переходим к расчету")
            return BaseCalculatorDialog.perform_calculation(calculator_class, session_id, chat_states)
            
        except Exception as e:
            base_logger.error(f"Ошибка в start_dialog: {str(e)}")
            base_logger.error(f"Traceback: {traceback.format_exc()}")
            return "Произошла ошибка при запуске диалога. Попробуйте еще раз."
    
    @staticmethod  
    def process_dialog(calculator_class, user_input, session_id, chat_states):
        """
        Обрабатывает ответ пользователя в рамках активного диалога
        """
        try:
            base_logger.info(f"Обработка ввода '{user_input}' для калькулятора '{calculator_class.NAME}', сессия {session_id}")
            
            if session_id not in chat_states:
                base_logger.error(f"Сессия {session_id} не найдена в chat_states")
                return "Сессия не найдена. Начните диалог заново."
                
            current_stage = chat_states[session_id].get("stage", "")
            current_data = chat_states[session_id].get("data", {})
            
            base_logger.debug(f"Текущий этап: {current_stage}, данные: {current_data}")
            
            if not current_stage:
                base_logger.error("Текущий этап не определен")
                return "Ошибка состояния диалога. Начните заново."
            
            # Обрабатываем текущий шаг
            base_logger.debug(f"Обработка шага '{current_stage}'")
            value, success = calculator_class.match_user_input(current_stage, user_input)
            
            if not success:
                base_logger.warning(f"Не удалось обработать ввод '{user_input}' для шага '{current_stage}'")
                return f"Неверный ввод для шага {current_stage}. Попробуйте еще раз."
            
            # Сохраняем значение
            chat_states[session_id]["data"][current_stage] = value
            base_logger.debug(f"Сохранено значение для {current_stage}: {value}")
            
            # Находим следующий шаг
            current_index = calculator_class.DIALOG_STEPS.index(current_stage)
            
            if current_index + 1 < len(calculator_class.DIALOG_STEPS):
                # Есть следующий шаг
                next_stage = calculator_class.DIALOG_STEPS[current_index + 1]
                chat_states[session_id]["stage"] = next_stage
                
                base_logger.info(f"Переход к следующему шагу: {next_stage}")
                return calculator_class.STEP_MESSAGES.get(next_stage, f"Шаг {next_stage}")
            else:
                # Все шаги завершены
                base_logger.info("Все шаги завершены, переходим к расчету")
                return BaseCalculatorDialog.perform_calculation(calculator_class, session_id, chat_states)
                
        except Exception as e:
            base_logger.error(f"Ошибка в process_dialog: {str(e)}")
            base_logger.error(f"Traceback: {traceback.format_exc()}")
            return "Произошла ошибка при обработке ввода. Попробуйте еще раз."
    
    @staticmethod
    def perform_calculation(calculator_class, session_id, chat_states):
        """
        Выполняет финальный расчет и возвращает результат
        """
        try:
            base_logger.info(f"🔢 Начинаем perform_calculation для сессии {session_id}")
            
            if session_id not in chat_states:
                base_logger.error(f"❌ Сессия {session_id} не найдена в chat_states")
                return "Сессия не найдена."
            
            data = chat_states[session_id].get("data", {})
            base_logger.info(f"📊 Данные для расчета: {data}")
            
            if not data:
                base_logger.error("❌ Нет данных для расчета")
                return "Нет данных для расчета."
            
            # 🔧 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Проверяем класс калькулятора
            if not calculator_class:
                base_logger.error("❌ calculator_class is None")
                return "Ошибка: класс калькулятора не определен."
            
            if not hasattr(calculator_class, 'calculate'):
                base_logger.error(f"❌ {calculator_class} не имеет метода calculate")
                return "Ошибка: неподдерживаемый тип калькулятора."
            
            # Создаем экземпляр калькулятора с проверкой
            base_logger.info(f"🏭 Создаем экземпляр калькулятора {getattr(calculator_class, 'NAME', 'UNKNOWN')}")
            try:
                calculator = calculator_class()
                base_logger.info("✅ Экземпляр калькулятора создан успешно")
            except Exception as calc_init_error:
                base_logger.error(f"❌ Ошибка создания калькулятора: {str(calc_init_error)}")
                return "Ошибка инициализации калькулятора."
            
            # Выполняем расчет с детальной проверкой
            base_logger.info("⚡ Вызываем метод calculate()")
            try:
                calculation_result = calculator.calculate(data)
                base_logger.info(f"✅ Результат calculate(): {calculation_result}")
                
                if not calculation_result:
                    base_logger.error("❌ calculate() вернул пустой результат")
                    return "Ошибка при расчете: пустой результат."
                    
                if not isinstance(calculation_result, dict):
                    base_logger.error(f"❌ calculate() вернул неверный тип: {type(calculation_result)}")
                    return "Ошибка при расчете: неверный формат результата."
                    
            except Exception as calc_error:
                base_logger.error(f"❌ Ошибка в методе calculate(): {str(calc_error)}")
                base_logger.error(f"📋 Traceback calculate(): {traceback.format_exc()}")
                return f"Ошибка при расчете: {str(calc_error)}"
            
            # Форматируем результат с детальной проверкой
            base_logger.info("🎨 Вызываем метод format_result()")
            try:
                formatted_result = calculator.format_result(calculation_result)
                base_logger.info(f"✅ Отформатированный результат длиной {len(formatted_result) if formatted_result else 0} символов")
                
                if not formatted_result:
                    base_logger.error("❌ format_result() вернул пустой результат")
                    return "Ошибка при форматировании результата."
                    
                if not isinstance(formatted_result, str):
                    base_logger.error(f"❌ format_result() вернул неверный тип: {type(formatted_result)}")
                    formatted_result = str(formatted_result)
                    
            except Exception as format_error:
                base_logger.error(f"❌ Ошибка в методе format_result(): {str(format_error)}")
                base_logger.error(f"📋 Traceback format_result(): {traceback.format_exc()}")
                return f"Ошибка при форматировании: {str(format_error)}"
            
            # 🎯 ГЛАВНОЕ ИСПРАВЛЕНИЕ: Правильно устанавливаем этап
            base_logger.info("💾 Сохраняем результаты в сессии")
            chat_states[session_id]["calculation_result"] = formatted_result
            chat_states[session_id]["full_calc"] = calculation_result
            chat_states[session_id]["stage"] = "collect_contact"  # ← НЕ "completed"!
            
            base_logger.info(f"🔄 Этап установлен на: {chat_states[session_id]['stage']}")
            
            # Добавляем запрос контактных данных
            contact_request = "\n\n[SHOW_CONTACT_FORM]"
            final_result = formatted_result + contact_request
            
            base_logger.info("🎉 perform_calculation завершен успешно")
            return final_result
            
        except Exception as e:
            base_logger.error(f"💥 КРИТИЧЕСКАЯ ОШИБКА в perform_calculation: {str(e)}")
            base_logger.error(f"📋 Полный traceback: {traceback.format_exc()}")
            
            # Детальная диагностика
            try:
                base_logger.error(f"🔍 Диагностика:")
                base_logger.error(f"   - calculator_class: {calculator_class}")
                base_logger.error(f"   - calculator_class.NAME: {getattr(calculator_class, 'NAME', 'НЕ НАЙДЕН')}")
                base_logger.error(f"   - session_id: {session_id}")
                base_logger.error(f"   - chat_states keys: {list(chat_states.keys()) if chat_states else 'chat_states is None'}")
                
                if session_id in chat_states:
                    session_data = chat_states[session_id]
                    base_logger.error(f"   - session_data keys: {list(session_data.keys())}")
                    base_logger.error(f"   - data в сессии: {session_data.get('data', 'НЕТ ДАННЫХ')}")
                
            except Exception as diag_error:
                base_logger.error(f"⚠️  Ошибка даже в диагностике: {str(diag_error)}")
            
            return "Произошла ошибка при расчете. Попробуйте еще раз."