document.addEventListener('DOMContentLoaded', () => {
    const chatBox = document.getElementById('chat-box');
    const askForm = document.getElementById('ask-form');
    const questionTextarea = document.querySelector('.ask-form textarea');
    const sendButton = document.querySelector('.send-button');

    // Función para renderizar Markdown de un mensaje
    function renderMarkdown(element) {
        const markdownText = element.textContent;
        element.innerHTML = marked.parse(markdownText);
    }

    // Renderizar los mensajes existentes al cargar la página.
    document.querySelectorAll('.chat-message.bot').forEach(renderMarkdown);

    // Manejo del envío del formulario de la pregunta
    askForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const question = questionTextarea.value.trim();
        const ente = askForm.querySelector('select').value;

        if (question === '' || ente === '') {
            return;
        }

        // Agrega el mensaje del usuario a la caja de chat
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'chat-message user';
        userMessageDiv.textContent = `👤 ${question}`;
        chatBox.appendChild(userMessageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;

        // Crea un mensaje de carga para el bot
        const botMessageDiv = document.createElement('div');
        botMessageDiv.className = 'chat-message bot';
        botMessageDiv.textContent = '...';
        chatBox.appendChild(botMessageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;

        // Deshabilita el botón mientras se procesa la respuesta
        sendButton.disabled = true;

        try {
            const formData = new FormData();
            formData.append('question', question);
            formData.append('ente', ente);

            const response = await fetch('/ask', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            // Actualiza el mensaje del bot con la respuesta real y procesa el Markdown
            if (data.success) {
                botMessageDiv.textContent = data.answer;
                renderMarkdown(botMessageDiv);
            } else {
                botMessageDiv.textContent = data.message;
            }

        } catch (error) {
            console.error('Error al enviar la pregunta:', error);
            botMessageDiv.textContent = '⚠️ Hubo un error al obtener la respuesta.';
        } finally {
            // Habilita el botón y limpia el área de texto
            sendButton.disabled = false;
            questionTextarea.value = '';
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    });
});
