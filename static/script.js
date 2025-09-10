document.addEventListener('DOMContentLoaded', () => {
    const chatBox = document.getElementById('chat-box');
    const askForm = document.getElementById('ask-form');
    const uploadForm = document.getElementById('upload-form');
    const pdfInput = document.getElementById('pdfs');
    const questionTextarea = document.querySelector('.ask-form textarea');
    const fileLabelText = document.getElementById('file-label-text');
    const sendButton = document.querySelector('.send-button');
    const enteSelect = document.querySelector('.ask-form select');

    // Función para renderizar Markdown de un mensaje
    function renderMarkdown(element) {
        const markdownText = element.textContent;
        element.innerHTML = marked.parse(markdownText);
    }
    
    // Renderizar los mensajes existentes al cargar la página.
    document.querySelectorAll('.chat-message.bot').forEach(renderMarkdown);

    // Función para actualizar el texto del botón del PDF
    function updateFileName(input) {
        if (input.files.length > 0) {
            fileLabelText.textContent = input.files.length > 1 ? `${input.files.length} archivos seleccionados` : input.files[0].name;
        } else {
            fileLabelText.textContent = '📄 Seleccionar PDF';
        }
    }

    // Escucha el cambio en el input de archivo para actualizar el texto del botón.
    pdfInput.addEventListener('change', (event) => {
        updateFileName(event.target);
    });

    // Manejo del envío del formulario de subida de PDF
    uploadForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const formData = new FormData(uploadForm);
        
        sendButton.disabled = true;

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
            });
            const result = await response.json();
            
            if (result.success) {
                console.log(result.message);
                // Aquí podrías mostrar una notificación de éxito
            } else {
                console.error(result.message);
                // Aquí podrías mostrar un mensaje de error
            }
        } catch (error) {
            console.error('Error al subir el archivo:', error);
        } finally {
            sendButton.disabled = false;
        }
    });

    // Manejo del envío del formulario de la pregunta
    askForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        const question = questionTextarea.value.trim();
        const ente = enteSelect.value;
        const pdfFiles = pdfInput.files;

        // Si hay archivos y no hay pregunta, envía el formulario de subida
        if (pdfFiles.length > 0 && question === '') {
            uploadForm.submit();
            return;
        }

        // Si no hay pregunta ni archivos, no hagas nada
        if (question === '') {
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
