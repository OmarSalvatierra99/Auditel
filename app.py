import os
import urllib.parse
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from dotenv import load_dotenv
from openai import OpenAI

# Cargar variables de entorno
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))

# Funciones de historial en sesión
def get_chat_history():
    return session.get("chat_history", [])

def set_chat_history(history):
    session["chat_history"] = history

# Wrapper OpenAI con manejo de errores humanos
def preguntar_openai(messages):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[ERROR OpenAI] {e}")
        return "⚠️ El sistema se saturó o hubo un problema con OpenAI, por favor inténtelo más tarde."

# Generar enlace al Periódico Oficial de Tlaxcala
def generar_enlace_busqueda_periodico(query):
    if not query.strip():
        return None
    palabras = [palabra for palabra in query.split() if len(palabra) > 2]
    keywords = palabras[:5]
    search_string = " ".join(keywords)
    search_encoded = urllib.parse.quote_plus(search_string)
    url = f"https://periodico.tlaxcala.gob.mx/index.php/buscar?texto={search_encoded}"
    return url

# Rutas
@app.route("/", methods=["GET"])
def index():
    chat_history = get_chat_history()
    return render_template("index.html", chat_history=chat_history)

@app.route("/ask", methods=["POST"])
def ask():
    question = request.form.get("question")
    ente = request.form.get("ente")

    if not question:
        return jsonify({"success": False, "message": "Por favor escribe una pregunta."})
    if not ente:
        return jsonify({"success": False, "message": "Selecciona un tipo de ente."})

    chat_history = get_chat_history()

    # Prompts base según tipo de ente
    ente_context = {
        "autonomo": "Eres un asistente experto en la legislación y documentación de entes autónomos en Tlaxcala. Responde a la pregunta del usuario con base en tu conocimiento general de este tema.",
        "paraestatal": "Eres un asistente experto en la legislación y documentación de entidades paraestatales en Tlaxcala. Responde a la pregunta del usuario con base en tu conocimiento general de este tema.",
        "centralizada": "Eres un asistente experto en la legislación y documentación de dependencias centralizadas en Tlaxcala. Responde a la pregunta del usuario con base en tu conocimiento general de este tema.",
        "desconcentrada": "Eres un asistente experto en la legislación y documentación de dependencias desconcentradas en Tlaxcala. Responde a la pregunta del usuario con base en tu conocimiento general de este tema.",
        "descentralizada": "Eres un asistente experto en la legislación y documentación de entidades descentralizadas en Tlaxcala. Responde a la pregunta del usuario con base en tu conocimiento general de este tema."
    }

    # Mejorar el prompt para que el modelo responda con su base de conocimiento
    system_prompt = ente_context.get(ente, "Eres un asistente experto en la legislación y documentación de Tlaxcala. Responde a la pregunta del usuario con base en tu conocimiento general de este tema.")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Pregunta: {question}"}
    ]

    answer = preguntar_openai(messages)

    # Agregar hipervínculo al Periódico Oficial de Tlaxcala
    enlace_busqueda = generar_enlace_busqueda_periodico(question)
    if enlace_busqueda:
        answer += f'\n\n🔗 [Ver documentos relacionados en el Periódico Oficial de Tlaxcala]({enlace_busqueda})'

    if answer.startswith("⚠️"):
        return jsonify({"success": False, "message": answer})

    chat_history.append({"question": question, "answer_html": answer})
    set_chat_history(chat_history)

    return jsonify({"success": True, "answer": answer})

@app.route("/clear", methods=["POST"])
def clear():
    session.clear()
    flash("🔄 Nueva sesión iniciada.", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5020, debug=True)
