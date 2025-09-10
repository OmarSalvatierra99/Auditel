import os
import urllib.parse
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from dotenv import load_dotenv
from openai import OpenAI
from PyPDF2 import PdfReader

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

# Extraer texto de PDFs
def extract_text_from_pdfs(files):
    text = ""
    for f in files:
        try:
            pdf = PdfReader(f)
            for page in pdf.pages:
                text += page.extract_text() or ""
        except Exception as e:
            print(f"[ERROR PDF] {e}")
    return text

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
    keywords = palabras[:5]  # limitar a 5 palabras clave
    search_string = " ".join(keywords)
    search_encoded = urllib.parse.quote_plus(search_string)
    url = f"https://periodico.tlaxcala.gob.mx/index.php/buscar?texto={search_encoded}"
    return url

# Rutas
@app.route("/", methods=["GET"])
def index():
    chat_history = get_chat_history()
    pdf_ready = session.get("pdf_ready", False)
    return render_template("index.html",
                           chat_history=chat_history,
                           pdf_ready=pdf_ready)

@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("pdfs")
    if not files or files[0].filename == "":
        return jsonify({"success": False, "message": "Debes seleccionar al menos un PDF."})

    text = extract_text_from_pdfs(files)
    if not text.strip():
        return jsonify({"success": False, "message": "No se pudo extraer texto de los PDFs."})

    session["pdf_text"] = text
    session["pdf_ready"] = True
    set_chat_history([])
    return jsonify({"success": True, "message": "✅ PDFs cargados correctamente."})

@app.route("/ask", methods=["POST"])
def ask():
    question = request.form.get("question")
    ente = request.form.get("ente")

    if not question:
        return jsonify({"success": False, "message": "Por favor escribe una pregunta."})
    if not ente:
        return jsonify({"success": False, "message": "Selecciona un tipo de ente."})

    chat_history = get_chat_history()
    pdf_text = session.get("pdf_text", "")

    # Prompts base según tipo de ente (solo clasificar la documentación)
    ente_context = {
        "autonomo": "Clasifica la documentación como perteneciente a un Ente Autónomo, aplica normativa específica para órganos autónomos estatales.",
        "paraestatal": "Clasifica la documentación como perteneciente a una entidad Paraestatal, aplica normativa específica para empresas y organismos estatales.",
        "centralizada": "Clasifica la documentación como perteneciente a una Dependencia Centralizada, aplica normativa de Secretarías y unidades centrales.",
        "desconcentrada": "Clasifica la documentación como perteneciente a una Dependencia Desconcentrada, aplica normativa de delegaciones y oficinas regionales.",
        "descentralizada": "Clasifica la documentación como perteneciente a una Entidad Descentralizada, aplica normativa de universidades, institutos y hospitales estatales."
    }

    system_prompt = ente_context.get(ente, "Clasifica la documentación según el ente correspondiente.")

    # Construir mensajes para OpenAI
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    if pdf_text.strip():
        messages.append({"role": "user", "content": f"Documentación cargada:\n{pdf_text}"})
    else:
        messages.append({"role": "user", "content": "⚠️ No hay PDF cargado, clasifica la documentación de forma general."})

    messages.append({"role": "user", "content": f"Pregunta: {question}"})

    answer = preguntar_openai(messages)

    # Agregar hipervínculo al Periódico Oficial de Tlaxcala
    enlace_busqueda = generar_enlace_busqueda_periodico(question)
    if enlace_busqueda:
        answer += f'\n\n🔗 [Ver documentos relacionados en el Periódico Oficial de Tlaxcala]({enlace_busqueda})'

    # Manejo de errores humanos
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
