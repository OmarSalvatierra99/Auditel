import os
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from dotenv import load_dotenv
from openai import OpenAI
from scripts.busqueda_web import buscar_en_periodico_tlaxcala, buscar_en_dof

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

# Wrapper OpenAI con manejo de errores y formato JSON
def preguntar_openai(messages):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={ "type": "json_object" }
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return data
    except Exception as e:
        print(f"[ERROR OpenAI] {e}")
        return {"answer": "⚠️ El sistema experimentó un error. Por favor, inténtelo más tarde.", "keywords": ""}

# Rutas
@app.route("/", methods=["GET"])
def index():
    chat_history = get_chat_history()
    return render_template("index.html", chat_history=chat_history)

@app.route("/ask", methods=["POST"])
def ask():
    question = request.form.get("question")
    ente = request.form.get("ente")
    auditoria = request.form.get("auditoria")

    if not question:
        return jsonify({"success": False, "message": "Por favor escribe una pregunta."})
    if not ente:
        return jsonify({"success": False, "message": "Selecciona un tipo de ente."})
    if not auditoria:
        return jsonify({"success": False, "message": "Selecciona un tipo de auditoría."})

    chat_history = get_chat_history()

    ente_context = {
        "autonomo": f"Eres un asistente experto en legislación de entes autónomos en Tlaxcala, con especialización en auditoría {auditoria}. Responde de manera argumentada y extrae palabras clave relevantes para búsquedas oficiales. Devuelve un JSON con: 'answer' (respuesta completa) y 'keywords' (lista de palabras clave).",
        "paraestatal / descentralizada": f"Eres un asistente experto en legislación de entidades paraestatales / descentralizadas en Tlaxcala, con especialización en auditoría {auditoria}. Responde de manera argumentada y extrae palabras clave relevantes para búsquedas oficiales. Devuelve un JSON con: 'answer' (respuesta completa) y 'keywords' (lista de palabras clave).",
        "centralizada": f"Eres un asistente experto en legislación de dependencias centralizadas en Tlaxcala, con especialización en auditoría {auditoria}. Responde de manera argumentada y extrae palabras clave relevantes para búsquedas oficiales. Devuelve un JSON con: 'answer' (respuesta completa) y 'keywords' (lista de palabras clave).",
    }

    system_prompt = ente_context.get(ente, f"Eres un asistente experto en legislación de Tlaxcala, con especialización en auditoría {auditoria}. Responde de manera argumentada y extrae palabras clave relevantes. Devuelve un JSON con: 'answer' (respuesta) y 'keywords' (lista de palabras clave).")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Pregunta: {question}"}
    ]

    data = preguntar_openai(messages)
    answer = data.get("answer", "No se pudo generar una respuesta.")
    keywords = data.get("keywords", question)

    if answer.startswith("⚠️"):
        return jsonify({"success": False, "message": answer})

    # Convertir keywords a string si es una lista
    if isinstance(keywords, list):
        keywords_str = " ".join(keywords)
    else:
        keywords_str = keywords

    # Búsquedas web con palabras clave
    enlace_tlaxcala = buscar_en_periodico_tlaxcala(keywords_str)
    enlace_dof = buscar_en_dof(keywords_str)

    # El back-end solo envía los enlaces, la renderización se hace en el front-end
    links_markdown = f'\n\n🔗 [Documentos en el Periódico Oficial de Tlaxcala]({enlace_tlaxcala})'
    links_markdown += f'\n🔗 [Documentos en el Diario Oficial de la Federación]({enlace_dof})'
    
    # Se guarda el texto original sin procesar en el historial
    chat_history.append({"question": question, "answer_raw": answer, "links_raw": links_markdown})
    set_chat_history(chat_history)

    # Se envía el texto original y los enlaces para que el front-end los combine
    return jsonify({"success": True, "answer": answer, "links": links_markdown})

@app.route("/clear", methods=["POST"])
def clear():
    session.clear()
    flash("🔄 Nueva sesión iniciada.", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5020, debug=True)
