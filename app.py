import os
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from dotenv import load_dotenv
from openai import OpenAI
import re

# Cargar variables de entorno
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))

# Cargar las bases de datos desde la carpeta 'data'
DB_AUDITORIA = {}
DATA_DIR = "data"
for filename in os.listdir(DATA_DIR):
    if filename.endswith(".json"):
        with open(os.path.join(DATA_DIR, filename), 'r', encoding='utf-8') as f:
            nombre_base = os.path.splitext(filename)[0].replace("_", " ").title()
            DB_AUDITORIA[nombre_base] = json.load(f)

# Funciones de historial en sesión
def get_chat_history():
    return session.get("chat_history", [])

def set_chat_history(history):
    session["chat_history"] = history

# Extracción simple de palabras clave
def get_keywords(text):
    # Remueve signos de puntuación y convierte a minúsculas
    text = re.sub(r'[^\w\s]', '', text.lower())
    # Retorna palabras únicas con al menos 3 caracteres
    return list(set(word for word in text.split() if len(word) > 2))

# Filtra la base de datos por palabras clave
def filter_db(db, keywords):
    if not keywords:
        return []
    
    # Filtra registros donde alguna palabra clave esté en 'tipo' o 'descripcion_irregularidad'
    filtered = [
        item for item in db
        if any(keyword in item.get('tipo', '').lower() or 
               keyword in item.get('descripcion_irregularidad', '').lower()
               for keyword in keywords)
    ]
    return filtered

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
    tipos_auditoria = list(DB_AUDITORIA.keys())
    return render_template("index.html", chat_history=chat_history, tipos_auditoria=tipos_auditoria)

@app.route("/ask", methods=["POST"])
def ask():
    question = request.form.get("question")
    ente = request.form.get("ente")
    auditoria_tipo = request.form.get("auditoria")

    if not question:
        return jsonify({"success": False, "message": "Por favor escribe una pregunta."})
    if not ente:
        return jsonify({"success": False, "message": "Selecciona un tipo de ente."})
    if not auditoria_tipo:
        return jsonify({"success": False, "message": "Selecciona un tipo de auditoría."})

    chat_history = get_chat_history()
    
    db_to_use = DB_AUDITORIA.get(auditoria_tipo, [])
    
    # Extrae palabras clave de la pregunta
    keywords = get_keywords(question)
    
    # Filtra la base de datos para enviar solo los registros relevantes
    filtered_db = filter_db(db_to_use, keywords)
    
    db_string = json.dumps(filtered_db, indent=2, ensure_ascii=False)

    system_prompt = f"""
    Eres un asistente experto en legislación de Tlaxcala, especializado en auditoría {auditoria_tipo} para entes de tipo "{ente}".
    Tu tarea es **consultar la base de datos de conceptos proporcionada**, analizar la pregunta del usuario y generar una respuesta experta.
    
    La base de datos tiene este formato:
    ```json
    {db_string}
    ```
    
    Instrucciones:
    1.  Identifica los conceptos clave en la pregunta del usuario.
    2.  Busca en la base de datos los registros que coincidan con el tipo de ente y los conceptos clave.
    3.  Si encuentras coincidencias, formula una respuesta que incluya la **normativa específica** y una **observación** relevante basada en esa normativa. La observación debe ser una conclusión experta sobre cómo aplicar la normativa.
    4.  Si no encuentras una coincidencia directa, genera una respuesta experta y general sobre el tema, mencionando la importancia de la normativa aplicable sin citar una específica.
    5.  Tu respuesta debe ser un objeto JSON con dos claves:
        -   `answer`: La respuesta completa, clara y argumentada.
        -   `keywords`: Una lista de palabras clave extraídas de la pregunta y la normativa encontrada.
    
    Ejemplo de respuesta:
    {{
        "answer": "De acuerdo con el registro encontrado, si un ente paraestatal descentralizado recibe recursos federales, está obligado a presentar informes trimestrales de rendición de cuentas, conforme al Capítulo V de las Reglas de Operación del Programa. Una observación importante para la auditoría es verificar que estos informes se presenten en tiempo y forma, y que los gastos estén alineados con los objetivos del programa.",
        "keywords": ["rendición de cuentas", "recursos federales", "informes trimestrales", "Reglas de Operación"]
    }}
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Pregunta: {question}"}
    ]

    data = preguntar_openai(messages)
    answer = data.get("answer", "No se pudo generar una respuesta.")

    chat_history.append({"question": question, "answer_raw": answer})
    set_chat_history(chat_history)

    return jsonify({"success": True, "answer": answer})

@app.route("/clear", methods=["POST"])
def clear():
    session.clear()
    flash("🔄 Nueva sesión iniciada.", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5020, debug=True)
