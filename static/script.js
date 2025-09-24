document.addEventListener("DOMContentLoaded", function() {
    const askForm = document.getElementById("ask-form");
    const chatBox = document.getElementById("chat-box");
    const welcomeMessage = document.querySelector(".welcome-message");
    const suggestionsArea = document.getElementById("suggestions-area");
    const suggestionsContainer = document.getElementById("suggestions-container");
    const refreshSuggestionsBtn = document.getElementById("refresh-suggestions");

    const questionTextarea = askForm.querySelector('textarea[name="question"]');
    const sendButton = askForm.querySelector('.send-button');

    // Campos ocultos SOLO para auditoría y ente (NO para irregularidad)
    const auditoriaInput = document.createElement("input");
    auditoriaInput.type = "hidden";
    auditoriaInput.name = "auditoria";
    askForm.appendChild(auditoriaInput);

    const enteInput = document.createElement("input");
    enteInput.type = "hidden";
    enteInput.name = "ente";
    askForm.appendChild(enteInput);

    // Estado de la conversación
    const conversationState = {
        auditoria: null,
        ente: null,
        configuracionCompleta: false
    };

    // Inicializar elementos del formulario
    function inicializarFormulario() {
        questionTextarea.style.display = 'none';
        sendButton.style.display = 'none';
        questionTextarea.disabled = true;
        sendButton.disabled = true;
        questionTextarea.value = '';
        suggestionsArea.style.display = 'none';
    }

    inicializarFormulario();

    function showBotMessage(messageHtml) {
        const botMessageDiv = document.createElement("div");
        botMessageDiv.className = "chat-message bot";
        botMessageDiv.innerHTML = messageHtml;
        chatBox.appendChild(botMessageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
        return botMessageDiv;
    }

    function showUserMessage(messageText) {
        const userMessageDiv = document.createElement("div");
        userMessageDiv.className = "chat-message user";
        userMessageDiv.innerHTML = `
            <div class="message-header">👤 Tú</div>
            <div class="message-content">${escapeHtml(messageText)}</div>
        `;
        chatBox.appendChild(userMessageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function createSelectionButtons(options, onSelectCallback) {
        const buttonsContainer = document.createElement('div');
        buttonsContainer.className = 'selection-buttons';

        options.forEach(option => {
            const button = document.createElement('button');
            button.type = 'button';
            button.textContent = option.text;
            button.setAttribute('data-value', option.value);
            button.addEventListener('click', () => {
                buttonsContainer.querySelectorAll('button').forEach(btn => {
                    btn.disabled = true;
                });
                onSelectCallback(option.value, option.text);
            });
            buttonsContainer.appendChild(button);
        });

        return buttonsContainer;
    }

    function cargarSugerenciasPreguntas() {
        if (!conversationState.auditoria) {
            suggestionsArea.style.display = 'none';
            return;
        }

        const url = `/sugerir_preguntas?auditoria_tipo=${encodeURIComponent(conversationState.auditoria)}&ente_tipo=${encodeURIComponent(conversationState.ente || 'No especificado')}`;

        suggestionsContainer.innerHTML = '<div class="loading-suggestions">💭 Generando sugerencias...</div>';
        suggestionsArea.style.display = 'block';

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.preguntas && data.preguntas.length > 0) {
                    suggestionsContainer.innerHTML = '';
                    data.preguntas.forEach((pregunta, index) => {
                        const suggestionBtn = document.createElement('button');
                        suggestionBtn.type = 'button';
                        suggestionBtn.className = 'suggestion-btn';
                        suggestionBtn.innerHTML = `💡 ${escapeHtml(pregunta)}`;
                        suggestionBtn.addEventListener('click', () => {
                            questionTextarea.value = pregunta;
                            questionTextarea.style.height = 'auto';
                            questionTextarea.style.height = (questionTextarea.scrollHeight) + 'px';
                            questionTextarea.focus();
                        });
                        suggestionsContainer.appendChild(suggestionBtn);
                    });
                } else {
                    suggestionsContainer.innerHTML = '<div class="loading-suggestions">⚠️ No se pudieron generar sugerencias</div>';
                }
            })
            .catch(error => {
                console.error("Error cargando sugerencias:", error);
                suggestionsContainer.innerHTML = '<div class="loading-suggestions">❌ Error al cargar sugerencias</div>';
            });
    }

    function handleAuditoriaSelection(value, text) {
        showUserMessage(`Tipo de auditoría: ${text}`);
        conversationState.auditoria = value;
        auditoriaInput.value = value;

        if (value === 'Financiera') {
            // Para auditoría financiera, preguntar tipo de ente
            const entePrompt = showBotMessage(`
                <div class="message-header">🔍 Auditel</div>
                <div class="message-content">
                    <p>💰 <strong>Auditoría Financiera seleccionada</strong></p>
                    <p>Para brindarte respuestas más precisas, selecciona el tipo de ente:</p>
                </div>
            `);
            
            const enteButtons = createSelectionButtons(
                [
                    { text: '🏛️ Ente Autónomo', value: 'Autónomo' },
                    { text: '🏢 Paraestatal/Descentralizada', value: 'Paraestatal' },
                    { text: '📊 Centralizada', value: 'Centralizada' },
                    { text: '❓ No especificar', value: 'No especificado' }
                ],
                handleEnteSelection
            );
            entePrompt.appendChild(enteButtons);
        } else {
            // Para obra pública, ir directamente a preguntas
            conversationState.ente = 'No aplica';
            enteInput.value = 'No aplica';
            showQuestionForm();
        }
    }

    function handleEnteSelection(value, text) {
        showUserMessage(`Tipo de ente: ${text}`);
        conversationState.ente = value;
        enteInput.value = value;
        showQuestionForm();
    }

    function showQuestionForm() {
        conversationState.configuracionCompleta = true;

        showBotMessage(`
            <div class="message-header">🔍 Auditel</div>
            <div class="message-content">
                <p>✅ <strong>¡Configuración completada!</strong></p>
                <p>Ahora puedo ayudarte con:</p>
                <ul>
                    <li>🔍 <strong>Detección automática</strong> de irregularidades</li>
                    <li>⚖️ <strong>Normativa aplicable</strong> según tu caso</li>
                    <li>📋 <strong>Recomendaciones técnicas</strong> específicas</li>
                </ul>
                <p>Contexto configurado:</p>
                <ul>
                    <li>🏛️ <strong>Auditoría:</strong> ${conversationState.auditoria}</li>
                    ${conversationState.ente ? `<li>📋 <strong>Ente:</strong> ${conversationState.ente}</li>` : ''}
                </ul>
                <p>Escribe tu pregunta y detectaré automáticamente la irregularidad y normativa aplicable.</p>
            </div>
        `);

        // Mostrar elementos del formulario
        questionTextarea.style.display = 'block';
        sendButton.style.display = 'flex';
        questionTextarea.disabled = false;
        sendButton.disabled = false;
        questionTextarea.style.height = '50px';
        questionTextarea.focus();

        // Cargar sugerencias
        setTimeout(cargarSugerenciasPreguntas, 500);
    }

    // Configurar auto-expansión del textarea
    questionTextarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // Configurar envío con Enter (sin Shift)
    questionTextarea.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (conversationState.configuracionCompleta && this.value.trim()) {
                askForm.dispatchEvent(new Event('submit'));
            }
        }
    });

    // Botón de refresh de sugerencias
    if (refreshSuggestionsBtn) {
        refreshSuggestionsBtn.addEventListener('click', function(e) {
            e.preventDefault();
            cargarSugerenciasPreguntas();
        });
    }

    // Manejar envío del formulario
    askForm.addEventListener("submit", function(event) {
        event.preventDefault();

        const question = questionTextarea.value.trim();

        if (!question) {
            showBotMessage(`
                <div class="message-header">🔍 Auditel</div>
                <div class="message-content">
                    <p>⚠️ Por favor, escribe tu pregunta.</p>
                </div>
            `);
            questionTextarea.focus();
            return;
        }

        if (!conversationState.configuracionCompleta) {
            showBotMessage(`
                <div class="message-header">🔍 Auditel</div>
                <div class="message-content">
                    <p>⚠️ Por favor, completa la configuración inicial primero.</p>
                </div>
            `);
            return;
        }

        // Mostrar mensaje del usuario
        showUserMessage(question);

        // Mostrar estado de carga con información de detección
        const loadingMessageDiv = showBotMessage(`
            <div class="message-header">🔍 Auditel</div>
            <div class="message-content">
                <div class="loading-message">
                    <p>🔍 <strong>Analizando tu consulta...</strong></p>
                    <div class="loading-spinner"></div>
                    <p><small>Detectando irregularidad y normativa aplicable en ${conversationState.auditoria}</small></p>
                </div>
            </div>
        `);

        // Deshabilitar formulario durante el envío
        questionTextarea.disabled = true;
        sendButton.disabled = true;
        sendButton.innerHTML = '⏳';
        suggestionsArea.style.display = 'none';

        // Preparar datos del formulario - SOLO auditoría y ente
        const formData = new FormData();
        formData.append("question", question);
        formData.append("auditoria", conversationState.auditoria);
        formData.append("ente", conversationState.ente || "No especificado");

        // Enviar solicitud
        fetch("/ask", {
            method: "POST",
            body: formData,
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            loadingMessageDiv.remove();

            if (data.success) {
                // Renderizar respuesta de forma segura
                let answerContent = data.answer;
                if (typeof marked !== 'undefined') {
                    answerContent = marked.parse(data.answer);
                }

                const irregularidadInfo = data.irregularidad_detectada && data.irregularidad_detectada !== 'No detectada' 
                    ? `<div class="detection-badge">🔍 Irregularidad detectada: <strong>${data.irregularidad_detectada}</strong></div>`
                    : '';

                const botResponse = showBotMessage(`
                    <div class="message-header">🔍 Auditel</div>
                    <div class="message-content">${answerContent}</div>
                    ${irregularidadInfo}
                    <div class="message-context">
                        <small>Contexto: ${conversationState.auditoria} • ${conversationState.ente || 'No aplica'} • Detección automática</small>
                    </div>
                `);
            } else {
                showBotMessage(`
                    <div class="message-header">🔍 Auditel</div>
                    <div class="message-content">
                        <p>❌ Error: ${data.message || 'Error desconocido'}</p>
                    </div>
                `);
            }
        })
        .catch(error => {
            console.error("Error:", error);
            loadingMessageDiv.remove();
            showBotMessage(`
                <div class="message-header">🔍 Auditel</div>
                <div class="message-content">
                    <p>❌ Error de conexión: ${error.message}</p>
                    <p>Por favor, verifica tu conexión e intenta nuevamente.</p>
                </div>
            `);
        })
        .finally(() => {
            // Restablecer formulario
            questionTextarea.disabled = false;
            sendButton.disabled = false;
            sendButton.innerHTML = '➤';
            questionTextarea.value = "";
            questionTextarea.style.height = '50px';
            questionTextarea.focus();

            // Recargar sugerencias
            if (conversationState.configuracionCompleta) {
                setTimeout(cargarSugerenciasPreguntas, 1000);
            }

            chatBox.scrollTop = chatBox.scrollHeight;
        });
    });

    function startConversation() {
        if (welcomeMessage) {
            welcomeMessage.style.display = "none";
        }

        const disclaimer = document.querySelector('.disclaimer-message');
        if (disclaimer) {
            disclaimer.style.display = 'block';
        }

        const auditoriaPrompt = showBotMessage(`
            <div class="message-header">🔍 Auditel</div>
            <div class="message-content">
                <p>👋 ¡Hola! Soy <strong>Auditel</strong>, tu asistente inteligente especializado en auditoría.</p>
                <p>Para brindarte respuestas precisas con <strong>detección automática de irregularidades</strong>, por favor selecciona el tipo de auditoría:</p>
            </div>
        `);

        const auditoriaButtons = createSelectionButtons(
            [
                { text: '🏗️ Obra Pública', value: 'Obra Pública' },
                { text: '💰 Financiera', value: 'Financiera' }
            ],
            handleAuditoriaSelection
        );
        auditoriaPrompt.appendChild(auditoriaButtons);
    }

    // Iniciar conversación
    startConversation();
});
