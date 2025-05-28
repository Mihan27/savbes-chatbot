// Решение в двух файлах:

// 1. Вставить в нужное место страницы через блок HTML:
// <div id="savbes-chat-container"></div>

// 2. Затем использовать этот скрипт, который будет искать нужный контейнер:
(function() {
    // Дожидаемся полной загрузки DOM
    document.addEventListener('DOMContentLoaded', initChat);
    
    // Если DOM уже загружен, инициализируем чат сразу
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        initChat();
    }
    
    function initChat() {
        // Конфигурация чат-бота
        const config = {
            apiUrl: "https://Mihan.pythonanywhere.com/api/chat",
            botName: 'САВБЕС Ассистент',
            primaryColor: '#ff7043', // Оранжевый цвет САВБЕС
            welcomeMessage: 'Здравствуйте! Я виртуальный помощник компании САВБЕС. Чем могу помочь? Вы можете спросить о наших услугах, ценах или процессе работы.'
        };

        // Временные данные пользователя (очищаются при обновлении страницы)
        let userData = {
            name: null,
            phone: null,
            email: null
        };

        // Создаем стили для чат-бота в стиле Tilda блока
        const styles = document.createElement('style');
        styles.textContent = `
            .savbes-chat-block {
                width: 100%;
                max-width: 960px;
                margin: 50px auto;
                font-family: 'Arial', sans-serif;
                box-sizing: border-box;
                overflow: hidden;
                background-color: #ffffff;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
            }

            .savbes-chat-header {
                padding: 25px 30px;
                background-color: ${config.primaryColor};
                color: white;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }

            .savbes-chat-title {
                display: flex;
                flex-direction: column;
                gap: 5px;
            }

            .savbes-chat-title-main {
                font-size: 24px;
                font-weight: bold;
            }

            .savbes-chat-title-sub {
                font-size: 16px;
                opacity: 0.9;
            }

            .savbes-chat-messages {
                height: 350px;
                padding: 20px 30px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 15px;
                background-color: #f8f8f8;
                border: 1px solid #eeeeee;
            }

            .savbes-message {
                max-width: 80%;
                padding: 15px 20px;
                border-radius: 18px;
                margin-bottom: 5px;
                word-wrap: break-word;
                line-height: 1.5;
                font-size: 16px;
            }

            .savbes-assistant-message {
                background-color: white;
                align-self: flex-start;
                border-bottom-left-radius: 5px;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
            }

            .savbes-user-message {
                background-color: ${config.primaryColor};
                color: white;
                align-self: flex-end;
                border-bottom-right-radius: 5px;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            }

            .savbes-input-area {
                display: flex;
                padding: 20px 30px;
                background-color: white;
                border-top: 1px solid #eeeeee;
            }

            .savbes-user-input {
                flex-grow: 1;
                padding: 15px 20px;
                border: 1px solid #dddddd;
                border-radius: 30px;
                outline: none;
                font-size: 16px;
                background-color: #f8f8f8;
                transition: all 0.3s ease;
            }

            .savbes-user-input:focus {
                border-color: ${config.primaryColor};
                background-color: white;
                box-shadow: 0 0 5px rgba(255, 112, 67, 0.2);
            }

            .savbes-send-button {
                background-color: ${config.primaryColor};
                color: white;
                border: none;
                width: 50px;
                height: 50px;
                border-radius: 50%;
                margin-left: 15px;
                cursor: pointer;
                display: flex;
                justify-content: center;
                align-items: center;
                transition: all 0.3s ease;
                box-shadow: 0 3px 8px rgba(255, 112, 67, 0.3);
            }

            .savbes-send-button:hover {
                background-color: #ff5722;
                transform: translateY(-2px);
                box-shadow: 0 5px 12px rgba(255, 112, 67, 0.4);
            }

            .savbes-send-button svg {
                width: 22px;
                height: 22px;
                fill: white;
            }

            /* Стили для формы контактов */
            .savbes-contact-form {
                background-color: white;
                border-radius: 10px;
                padding: 20px 25px;
                margin-bottom: 15px;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
                align-self: center;
                width: 85%;
                border: 1px solid #eeeeee;
            }

            .savbes-form-title {
                font-weight: bold;
                margin-bottom: 15px;
                color: ${config.primaryColor};
                font-size: 18px;
            }

            .savbes-form-input {
                width: 100%;
                padding: 12px 15px;
                margin-bottom: 15px;
                border: 1px solid #dddddd;
                border-radius: 8px;
                box-sizing: border-box;
                font-size: 16px;
                background-color: #f8f8f8;
                transition: all 0.3s ease;
            }

            .savbes-form-input:focus {
                border-color: ${config.primaryColor};
                background-color: white;
                box-shadow: 0 0 5px rgba(255, 112, 67, 0.2);
            }

            .savbes-form-buttons {
                display: flex;
                justify-content: space-between;
                margin-top: 20px;
            }

            .savbes-form-submit, .savbes-form-cancel {
                padding: 12px 20px;
                border: none;
                border-radius: 30px;
                cursor: pointer;
                font-weight: 600;
                font-size: 16px;
                transition: all 0.3s ease;
            }

            .savbes-form-submit {
                background-color: ${config.primaryColor};
                color: white;
                flex-grow: 2;
                margin-right: 10px;
                box-shadow: 0 3px 8px rgba(255, 112, 67, 0.3);
            }

            .savbes-form-submit:hover {
                background-color: #ff5722;
                transform: translateY(-2px);
                box-shadow: 0 5px 12px rgba(255, 112, 67, 0.4);
            }

            .savbes-form-cancel {
                background-color: #f1f1f1;
                color: #555555;
                flex-grow: 1;
            }

            .savbes-form-cancel:hover {
                background-color: #e5e5e5;
            }

            /* Адаптивность */
            @media (max-width: 768px) {
                .savbes-chat-block {
                    margin: 30px auto;
                    width: 95%;
                }

                .savbes-chat-header {
                    padding: 20px;
                }

                .savbes-chat-title-main {
                    font-size: 20px;
                }

                .savbes-chat-messages {
                    height: 300px;
                    padding: 15px 20px;
                }

                .savbes-input-area {
                    padding: 15px 20px;
                }
            }

            @media (max-width: 480px) {
                .savbes-chat-block {
                    margin: 20px auto;
                    width: 100%;
                    border-radius: 0;
                }

                .savbes-chat-title-sub {
                    font-size: 14px;
                }

                .savbes-message {
                    font-size: 15px;
                    padding: 12px 15px;
                }

                .savbes-form-submit, .savbes-form-cancel {
                    padding: 10px 15px;
                    font-size: 15px;
                }
            }
        `;
        document.head.appendChild(styles);

        // Ищем целевой контейнер по ID
        const targetContainer = document.getElementById('savbes-chat-container');

        // Если контейнер не найден, выводим сообщение в консоль и выходим
        if (!targetContainer) {
            console.error('САВБЕС чат-бот: контейнер #savbes-chat-container не найден на странице');
            console.info('Добавьте <div id="savbes-chat-container"></div> в нужное место на странице');
            return;
        }

        // Создаем HTML-структуру чат-бота в стиле блока Tilda
        const chatElement = document.createElement('div');
        chatElement.className = 'savbes-chat-block';
        chatElement.innerHTML = `
            <div class="savbes-chat-header">
                <div class="savbes-chat-title">
                    <div class="savbes-chat-title-main">${config.botName}</div>
                    <div class="savbes-chat-title-sub">Задайте вопрос или закажите услугу</div>
                </div>
            </div>
            <div class="savbes-chat-messages" id="savbes-chat-messages">
                <div class="savbes-message savbes-assistant-message">
                    ${config.welcomeMessage}
                </div>
            </div>
            <div class="savbes-input-area">
                <input type="text" class="savbes-user-input" id="savbes-user-input" placeholder="Введите ваше сообщение...">
                <button class="savbes-send-button" id="savbes-send-button">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                    </svg>
                </button>
            </div>
        `;

        // Вставляем чат-бот в целевой контейнер
        targetContainer.appendChild(chatElement);

        // Генерируем уникальный ID сессии
        const sessionId = Math.random().toString(36).substring(2, 15);

        // ====== Функции для работы с формой контактов =======

        // Функция для показа формы контактов
        function showContactForm() {
            const messagesDiv = document.getElementById('savbes-chat-messages');
            
            // Создаем форму
            const formDiv = document.createElement('div');
            formDiv.className = 'savbes-contact-form';
            formDiv.innerHTML = `
                <div class="savbes-form-title">Оставьте ваши контактные данные</div>
                <input type="text" class="savbes-form-input" id="savbes-name-input" placeholder="Ваше имя">
                <input type="tel" class="savbes-form-input" id="savbes-phone-input" placeholder="Ваш телефон" required>
                <input type="email" class="savbes-form-input" id="savbes-email-input" placeholder="Ваш email (опционально)">
                <div class="savbes-form-buttons">
                    <button class="savbes-form-submit">Отправить</button>
                    <button class="savbes-form-cancel">Отмена</button>
                </div>
            `;
            
            // Добавляем форму в чат
            messagesDiv.appendChild(formDiv);
            
            // Прокручиваем чат вниз
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
            
            // Фокусируемся на поле ввода имени
            document.getElementById('savbes-name-input').focus();
            
            // Обработчики для кнопок
            formDiv.querySelector('.savbes-form-submit').addEventListener('click', function() {
                submitContactForm(formDiv);
            });
            
            formDiv.querySelector('.savbes-form-cancel').addEventListener('click', function() {
                // Удаляем форму
                formDiv.remove();
                
                // Отправляем отказ
                sendMessage('Не хочу оставлять контакты');
            });
            
            // Добавляем обработку Enter для отправки формы
            const phoneInput = document.getElementById('savbes-phone-input');
            phoneInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    submitContactForm(formDiv);
                }
            });
        }
        
        // Функция отправки данных формы
        function submitContactForm(formDiv) {
            const name = document.getElementById('savbes-name-input').value;
            const phone = document.getElementById('savbes-phone-input').value;
            const email = document.getElementById('savbes-email-input').value;
            
            if (phone) {
                // Удаляем форму
                formDiv.remove();
                
                // Сохраняем данные во временную переменную
                userData = {
                    name: name,
                    phone: phone,
                    email: email
                };
                
                // Заполняем формы на странице (однократно)
                fillPageForms(userData);
                
                // Отправляем данные в чат
                let contactText = ``;
                if (name) contactText += `${name}, `;
                contactText += `${phone}`;
                if (email) contactText += `, ${email}`;
                
                // Отправляем в чат
                sendMessage(contactText);
            } else {
                alert('Пожалуйста, введите номер телефона');
            }
        }

        // Функция для одноразового заполнения форм на странице
        function fillPageForms(data) {
            try {
                console.log("Заполнение форм на сайте данными из чат-бота:", data);
                
                // Заполняем все формы на странице
                document.querySelectorAll('form').forEach(function(form) {
                    // Пропускаем, если это форма самого чат-бота
                    if (form.closest('.savbes-chat-block')) {
                        return;
                    }
                    
                    // Заполняем поля телефона
                    if (data.phone) {
                        const phoneInputs = form.querySelectorAll('input[type="tel"], input[name="phone"], input[name*="PHONE"], input[placeholder*="елефон"], .t-input-phonemask');
                        phoneInputs.forEach(input => {
                            input.value = data.phone;
                            // Имитируем событие ввода для активации событий Tilda
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            console.log("Заполнено поле телефона:", input);
                        });
                    }
                    
                    // Заполняем поля имени
                    if (data.name) {
                        const nameInputs = form.querySelectorAll('input[name="name"], input[name*="NAME"], input[placeholder*="имя"], input[placeholder*="Имя"], input.t-input-name');
                        nameInputs.forEach(input => {
                            input.value = data.name;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            console.log("Заполнено поле имени:", input);
                        });
                    }
                    
                    // Заполняем поля email
                    if (data.email) {
                        const emailInputs = form.querySelectorAll('input[type="email"], input[name="email"], input[name*="EMAIL"], input[placeholder*="mail"], input[placeholder*="Mail"]');
                        emailInputs.forEach(input => {
                            input.value = data.email;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            console.log("Заполнено поле email:", input);
                        });
                    }
                });
                
                // Также ищем поля ввода вне форм
                if (data.phone) {
                    document.querySelectorAll('input[type="tel"]:not(form *), input[name*="phone"]:not(form *), input[placeholder*="елефон"]:not(form *)').forEach(input => {
                        // Пропускаем, если это поле самого чат-бота
                        if (input.closest('.savbes-chat-block')) {
                            return;
                        }
                        
                        console.log(`Найдено поле телефона вне формы:`, input);
                        input.value = data.phone;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    });
                }
                
                if (data.name) {
                    document.querySelectorAll('input[name*="name"]:not(form *), input[placeholder*="мя"]:not(form *)').forEach(input => {
                        // Пропускаем, если это поле самого чат-бота
                        if (input.closest('.savbes-chat-block')) {
                            return;
                        }
                        
                        console.log(`Найдено поле имени вне формы:`, input);
                        input.value = data.name;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    });
                }
                
                if (data.email) {
                    document.querySelectorAll('input[type="email"]:not(form *), input[name*="email"]:not(form *), input[placeholder*="mail"]:not(form *)').forEach(input => {
                        // Пропускаем, если это поле самого чат-бота
                        if (input.closest('.savbes-chat-block')) {
                            return;
                        }
                        
                        console.log(`Найдено поле email вне формы:`, input);
                        input.value = data.email;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    });
                }
            } catch (error) {
                console.error("Ошибка при заполнении форм:", error);
            }
        }

        // Функция для добавления сообщений в чат
        function addMessage(message, isUser) {
            const messagesDiv = document.getElementById('savbes-chat-messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `savbes-message ${isUser ? 'savbes-user-message' : 'savbes-assistant-message'}`;

            // Разбиваем сообщение на строки, если есть \n
            const formattedMessage = message.replace(/\n/g, '<br>');
            
            // Проверяем наличие метки формы
            if (!isUser && message.includes("[SHOW_CONTACT_FORM]")) {
                // Удаляем метку из сообщения
                const cleanMessage = message.replace("[SHOW_CONTACT_FORM]", "");
                messageDiv.innerHTML = cleanMessage;
                
                // Добавляем сообщение в чат
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
                
                // Показываем форму контактов с небольшой задержкой
                setTimeout(showContactForm, 500);
            } else {
                messageDiv.innerHTML = formattedMessage;
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
        }

        // Функция для отправки сообщения
        async function sendMessage(message) {
            if (!message.trim()) return;
            
            addMessage(message, true);
            document.getElementById('savbes-user-input').value = '';

            try {
                const response = await fetch(config.apiUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: message,
                        session_id: sessionId
                    })
                });

                const data = await response.json();
                
                // Обработка разных форматов ответа
                if (data && data.response) {
                    if (typeof data.response === 'object' && data.response.text) {
                        // Новый формат (вложенный объект)
                        addMessage(data.response.text, false);
                    } else {
                        // Старый формат (строка)
                        addMessage(data.response, false);
                    }
                } else {
                    addMessage("Извините, произошла ошибка при обработке ответа.", false);
                }
            } catch (error) {
                console.error('Error:', error);
                addMessage('Извините, произошла ошибка. Попробуйте позже.', false);
            }
        }

        // Добавляем обработчики событий
        const sendButton = document.getElementById('savbes-send-button');
        const userInput = document.getElementById('savbes-user-input');
        
        // Обработчик нажатия кнопки отправки
        if (sendButton) {
            sendButton.addEventListener('click', function() {
                const message = userInput.value.trim();
                if (message) {
                    sendMessage(message);
                }
            });
        }

        // Обработчик нажатия Enter
        if (userInput) {
            userInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    const message = this.value.trim();
                    if (message) {
                        sendMessage(message);
                    }
                }
            });
        }

        // Для удобства, прокручиваем сообщения вниз
        const messagesDiv = document.getElementById('savbes-chat-messages');
        if (messagesDiv) {
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        console.log('САВБЕС чат-бот успешно инициализирован в #savbes-chat-container');
    }
})();