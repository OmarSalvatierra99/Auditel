document.addEventListener("DOMContentLoaded", function() {
    const askForm = document.getElementById("ask-form");
    const chatBox = document.getElementById("chat-box");
    const welcomeMessage = document.querySelector(".welcome-message");

    // Renderiza el contenido del historial cuando la página carga
    document.querySelectorAll('.chat-message.bot[data-answer]').forEach(botMessageDiv => {
        const rawAnswer = botMessageDiv.getAttribute('data-answer');
        const rawLinks = botMessageDiv.getAttribute('data-links');
        const fullMarkdown = rawAnswer + rawLinks;
        botMessageDiv.innerHTML = marked.parse(fullMarkdown);
    });

    askForm.addEventListener("submit", function(event) {
        event.preventDefault();

        const formData = new FormData(askForm);
        const question = formData.get("question");
        const ente = formData.get("ente");
        const auditoria = formData.get("auditoria"); // Obtiene el nuevo campo

        if (!question || !ente || !auditoria) {
            alert("Por favor, completa todos los campos.");
            return;
        }

        // Muestra la pregunta del usuario al instante
        const userMessageDiv = document.createElement("div");
        userMessageDiv.className = "chat-message user";
        userMessageDiv.innerHTML = `👤 ${question}`;
        chatBox.appendChild(userMessageDiv);

        // Mensaje de carga mientras se espera la respuesta
        const loadingMessageDiv = document.createElement("div");
        loadingMessageDiv.className = "chat-message bot loading";
        loadingMessageDiv.innerHTML = "💬 Cargando...";
        chatBox.appendChild(loadingMessageDiv);

        // Desplaza al final
        chatBox.scrollTop = chatBox.scrollHeight;
        
        // Esconde el mensaje de bienvenida
        if (welcomeMessage) {
            welcomeMessage.style.display = "none";
        }

        // Deshabilita el formulario para evitar envíos múltiples
        askForm.querySelector("textarea").disabled = true;
        askForm.querySelector("button").disabled = true;

        fetch("/ask", {
            method: "POST",
            body: formData,
        })
        .then(response => response.json())
        .then(data => {
            // Elimina el mensaje de carga
            chatBox.removeChild(loadingMessageDiv);
            
            const botMessageDiv = document.createElement("div");
            botMessageDiv.className = "chat-message bot";
            
            if (data.success) {
                // Combina la respuesta y los enlaces y renderiza el Markdown
                const fullMarkdown = data.answer + data.links;
                botMessageDiv.innerHTML = marked.parse(fullMarkdown);
            } else {
                botMessageDiv.innerHTML = `⚠️ Error: ${data.message}`;
            }

            chatBox.appendChild(botMessageDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        })
        .catch(error => {
            console.error("Error:", error);
            chatBox.removeChild(loadingMessageDiv);
            const errorMessageDiv = document.createElement("div");
            errorMessageDiv.className = "chat-message bot";
            errorMessageDiv.innerHTML = "⚠️ Ocurrió un error en la comunicación con el servidor.";
            chatBox.appendChild(errorMessageDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        })
        .finally(() => {
            // Habilita el formulario de nuevo y limpia el textarea
            askForm.querySelector("textarea").disabled = false;
            askForm.querySelector("button").disabled = false;
            askForm.querySelector("textarea").value = "";
        });
    });
});
