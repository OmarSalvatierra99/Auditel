document.addEventListener("DOMContentLoaded", function() {
    const askForm = document.getElementById("ask-form");
    const chatBox = document.getElementById("chat-box");
    const welcomeMessage = document.querySelector(".welcome-message");
    const auditoriaSelect = askForm.querySelector('select[name="auditoria"]');
    const enteSelect = askForm.querySelector('select[name="ente"]');
    const questionTextarea = askForm.querySelector('textarea[name="question"]');
    const sendButton = askForm.querySelector('.send-button');

    // Deshabilita el formulario por defecto para controlar la interacción
    auditoriaSelect.style.display = 'none';
    enteSelect.style.display = 'none';
    questionTextarea.style.display = 'none';
    sendButton.style.display = 'none';

    // Función para mostrar un mensaje del bot en una burbuja
    function showBotMessage(messageHtml) {
        const botMessageDiv = document.createElement("div");
        botMessageDiv.className = "chat-message bot";
        botMessageDiv.innerHTML = messageHtml;
        chatBox.appendChild(botMessageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
        return botMessageDiv; // Devuelve el elemento por si se necesita manipular
    }

    // Función para mostrar un mensaje de usuario en una burbuja
    function showUserMessage(messageText) {
        const userMessageDiv = document.createElement("div");
        userMessageDiv.className = "chat-message user";
        userMessageDiv.innerHTML = `👤 ${messageText}`;
        chatBox.appendChild(userMessageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // Función para crear botones de selección
    function createSelectionButtons(options, onSelectCallback) {
        const buttonsContainer = document.createElement('div');
        buttonsContainer.className = 'selection-buttons';
        options.forEach(option => {
            const button = document.createElement('button');
            button.textContent = option.text;
            button.setAttribute('data-value', option.value);
            button.addEventListener('click', () => {
                onSelectCallback(option.value, option.text);
                buttonsContainer.style.display = 'none'; // Oculta los botones al seleccionar
            });
            buttonsContainer.appendChild(button);
        });
        return buttonsContainer;
    }

    // Lógica para el flujo de la conversación
    function startConversation() {
        if (welcomeMessage) {
            welcomeMessage.style.display = "none";
        }

        const auditoriaPrompt = showBotMessage(`
            <p>¡Hola! Soy Auditel, tu asistente experto en legislación de Tlaxcala. Para empezar, por favor, selecciona el tipo de auditoría.</p>
        `);
        const auditoriaButtons = createSelectionButtons(
            [{ text: 'Obra Pública', value: 'Obra Pública' }, { text: 'Financiera', value: 'Financiera' }],
            handleAuditoriaSelection
        );
        auditoriaPrompt.appendChild(auditoriaButtons);
    }

    function handleAuditoriaSelection(value, text) {
        showUserMessage(text);
        auditoriaSelect.value = value;
        if (value === 'Financiera') {
            const entePrompt = showBotMessage(`
                <p>Perfecto. Ahora, selecciona el tipo de ente.</p>
            `);
            const enteButtons = createSelectionButtons(
                [
                    { text: 'Ente Autónomo', value: 'Autónomo' },
                    { text: 'Paraestatal / Descentralizada', value: 'Paraestatal' },
                    { text: 'Centralizada', value: 'Centralizada' }
                ],
                handleEnteSelection
            );
            entePrompt.appendChild(enteButtons);
        } else {
            // Si es Obra Pública, el ente no es relevante, se asigna un valor por defecto
            enteSelect.value = 'Obra Pública';
            showQuestionForm();
        }
    }

    function handleEnteSelection(value, text) {
        showUserMessage(text);
        enteSelect.value = value;
        showQuestionForm();
    }

    function showQuestionForm() {
        showBotMessage(`
            <p>¡Excelente! Estoy listo para ayudarte. Por favor, escribe tu pregunta.</p>
        `);
        questionTextarea.style.display = 'block';
        sendButton.style.display = 'flex';
        questionTextarea.focus();
    }

    // Maneja el envío del formulario con la pregunta
    askForm.addEventListener("submit", function(event) {
        event.preventDefault();

        const formData = new FormData(askForm);
        const question = formData.get("question");

        if (!question) {
            alert("Por favor, escribe una pregunta.");
            return;
        }

        // Muestra la pregunta del usuario
        showUserMessage(question);

        // Mensaje de carga
        const loadingMessageDiv = showBotMessage("💬 Cargando...");
        loadingMessageDiv.classList.add('loading');

        // Deshabilita el formulario
        questionTextarea.disabled = true;
        sendButton.disabled = true;

        fetch("/ask", {
            method: "POST",
            body: formData,
        })
        .then(response => response.json())
        .then(data => {
            // Elimina el mensaje de carga
            loadingMessageDiv.remove();

            if (data.success) {
                // Renderiza la respuesta del bot con Markdown
                const botResponse = showBotMessage(marked.parse(data.answer));
            } else {
                showBotMessage(`⚠️ Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error("Error:", error);
            loadingMessageDiv.remove();
            showBotMessage("⚠️ Ocurrió un error en la comunicación con el servidor.");
        })
        .finally(() => {
            // Habilita el formulario y limpia el textarea
            questionTextarea.disabled = false;
            sendButton.disabled = false;
            questionTextarea.value = "";
            chatBox.scrollTop = chatBox.scrollHeight;
        });
    });

    // Llama a la función que inicia el flujo
    startConversation();
});
