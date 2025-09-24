import os
import json
import re
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from dotenv import load_dotenv
from functools import wraps

# Importar OpenAI correctamente para la versión 1.0+
try:
    from openai import OpenAI
    OPENAI_NEW_VERSION = True
except ImportError:
    import openai
    OPENAI_NEW_VERSION = False

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('auditel')

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))

# Configurar OpenAI para la nueva versión
if OPENAI_NEW_VERSION:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    openai_api_key = os.getenv("OPENAI_API_KEY")
else:
    openai.api_key = os.getenv("OPENAI_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    logger.warning("⚠️ OPENAI_API_KEY no encontrada en variables de entorno")

# Cargar las bases de datos desde la carpeta 'data'
DB_AUDITORIA = {}
DATA_DIR = "data"

# Mapeo de nombres de auditoría a nombres de archivo
AUDITORIA_FILES = {
    "Obra Pública": "obra_publica.json",
    "Financiera": "financiero.json"
}

# Manejo de errores para la carga de archivos
if not os.path.exists(DATA_DIR):
    logger.error(f"❌ Error: El directorio '{DATA_DIR}' no se encuentra.")
else:
    for auditoria_nombre, filename in AUDITORIA_FILES.items():
        file_path = os.path.join(DATA_DIR, filename)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    DB_AUDITORIA[auditoria_nombre] = json.load(f)
                    logger.info(f"✅ Archivo cargado: {filename} -> {auditoria_nombre} ({len(DB_AUDITORIA[auditoria_nombre])} registros)")
            except Exception as e:
                logger.error(f"❌ Error al leer {filename}: {e}")
        else:
            logger.error(f"❌ Archivo no encontrado: {file_path}")

# === FUNCIONES DE SEGURIDAD Y VALIDACIÓN ===

def sanitizar_texto(texto, max_length=2000):
    """Sanitiza texto eliminando caracteres peligrosos"""
    if not texto:
        return ""
    # Eliminar caracteres de control y espacios extra
    texto = re.sub(r'[\x00-\x1F\x7F]', '', texto.strip())
    texto = re.sub(r'\s+', ' ', texto)  # Normalizar espacios
    return texto[:max_length]

def validar_auditoria_tipo(tipo):
    """Valida que el tipo de auditoría sea válido"""
    tipos_validos = list(AUDITORIA_FILES.keys())
    return tipo if tipo in tipos_validos else None

def requiere_configuracion(f):
    """Decorator para verificar configuración inicial"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not openai_api_key:
            return jsonify({"success": False, "message": "Servicio de IA no configurado. Verifique OPENAI_API_KEY."})
        if not DB_AUDITORIA:
            return jsonify({"success": False, "message": "Bases de datos no cargadas correctamente."})
        return f(*args, **kwargs)
    return decorated_function

def log_solicitud(endpoint, datos):
    """Log de solicitudes para auditoría"""
    logger.info(f"{endpoint}: {datos}")

# === FUNCIONES DE MANEJO DE SESIÓN ===

def get_chat_history():
    return session.get("chat_history", [])

def set_chat_history(history):
    session["chat_history"] = history

# === FUNCIONES DE NEGOCIO MEJORADAS ===

def detectar_irregularidad_automatica(pregunta, auditoria_tipo, ente_tipo=None):
    """Detecta automáticamente el tipo de irregularidad basado en la pregunta"""
    if not pregunta or not auditoria_tipo:
        return None
    
    pregunta_lower = pregunta.lower()
    
    if auditoria_tipo not in DB_AUDITORIA:
        return None
    
    # Buscar coincidencias en la base de datos
    irregularidades = DB_AUDITORIA[auditoria_tipo]
    coincidencias = []
    
    for irregularidad in irregularidades:
        tipo = irregularidad.get('tipo', '').lower()
        descripcion = irregularidad.get('descripcion_irregularidad', '').lower()
        
        # Calcular puntaje de coincidencia
        puntaje = 0
        
        # Coincidencia exacta en tipo
        if tipo in pregunta_lower:
            puntaje += 10
        
        # Coincidencia de palabras clave en descripción
        palabras_descripcion = descripcion.split()
        for palabra in palabras_descripcion:
            if len(palabra) > 4 and palabra in pregunta_lower:
                puntaje += 2
        
        # Coincidencia con acciones de irregularidad
        acciones = irregularidad.get('acciones_irregularidad', [])
        for accion in acciones:
            if any(palabra in pregunta_lower for palabra in accion.lower().split() if len(palabra) > 4):
                puntaje += 1
        
        if puntaje > 0:
            coincidencias.append({
                'irregularidad': irregularidad,
                'puntaje': puntaje,
                'tipo': irregularidad.get('tipo')
            })
    
    # Ordenar por puntaje y retornar la mejor coincidencia
    if coincidencias:
        mejor_coincidencia = max(coincidencias, key=lambda x: x['puntaje'])
        if mejor_coincidencia['puntaje'] >= 3:  # Umbral mínimo
            return mejor_coincidencia['irregularidad']
    
    return None

def construir_contexto_mejorado(auditoria_tipo, irregularidad_detectada, pregunta, ente_tipo=None):
    """Construye un contexto más completo para OpenAI"""
    if auditoria_tipo not in DB_AUDITORIA:
        return "Información no disponible"
    
    contexto = f"CONTEXTO DE AUDITORÍA DETECTADO AUTOMÁTICAMENTE:\n"
    contexto += f"- Tipo de auditoría: {auditoria_tipo}\n"
    contexto += f"- Tipo de ente: {ente_tipo or 'No especificado'}\n"
    contexto += f"- Pregunta del usuario: {pregunta}\n\n"
    
    if irregularidad_detectada:
        contexto += f"IRREGULARIDAD DETECTADA: {irregularidad_detectada.get('tipo', 'No especificado')}\n\n"
        contexto += f"INFORMACIÓN ESPECÍFICA DE LA IRREGULARIDAD:\n"
        contexto += f"Descripción: {irregularidad_detectada.get('descripcion_irregularidad', 'No disponible')}\n"
        contexto += f"Acción promovida: {irregularidad_detectada.get('accion_promovida', 'No disponible')}\n"
        
        if irregularidad_detectada.get('acciones_irregularidad'):
            contexto += "Acciones de irregularidad:\n"
            for accion in irregularidad_detectada['acciones_irregularidad']:
                contexto += f"- {accion}\n"
        
        if irregularidad_detectada.get('documentacion_soporte'):
            contexto += "Documentación de soporte:\n"
            for doc in irregularidad_detectada['documentacion_soporte']:
                contexto += f"- {doc}\n"
        
        # Normatividad específica por tipo de auditoría
        contexto += "\nNORMATIVIDAD APLICABLE:\n"
        if auditoria_tipo == "Financiera":
            if irregularidad_detectada.get('normatividad_local'):
                contexto += f"📍 Normatividad local: {irregularidad_detectada['normatividad_local']}\n"
            if irregularidad_detectada.get('normatividad_federal'):
                contexto += f"🏛️ Normatividad federal: {irregularidad_detectada['normatividad_federal']}\n"
        
        elif auditoria_tipo == "Obra Pública":
            normas = []
            if irregularidad_detectada.get('normatividad_local_administracion_directa'):
                normas.append(f"📍 Local AD: {irregularidad_detectada['normatividad_local_administracion_directa']}")
            if irregularidad_detectada.get('normatividad_local_contrato'):
                normas.append(f"📍 Local Contrato: {irregularidad_detectada['normatividad_local_contrato']}")
            if irregularidad_detectada.get('normatividad_federal_administracion_directa'):
                normas.append(f"🏛️ Federal AD: {irregularidad_detectada['normatividad_federal_administracion_directa']}")
            if irregularidad_detectada.get('normatividad_federal_contratacion'):
                normas.append(f"🏛️ Federal Contrato: {irregularidad_detectada['normatividad_federal_contratacion']}")
            
            for norma in normas:
                contexto += f"- {norma}\n"
    else:
        contexto += "⚠️ No se detectó una irregularidad específica. Responder de forma general basándose en el tipo de auditoría.\n"
        contexto += "BASE DE CONOCIMIENTO DISPONIBLE:\n"
        for irregularidad in DB_AUDITORIA[auditoria_tipo][:5]:  # Primeras 5 irregularidades como referencia
            contexto += f"- {irregularidad.get('tipo', 'Sin nombre')}: {irregularidad.get('descripcion_irregularidad', '')[:100]}...\n"
    
    return contexto

def generar_respuesta_inteligente(pregunta, contexto, conversation_history):
    """Genera respuesta usando OpenAI con detección automática de irregularidad"""
    try:
        if not openai_api_key:
            return "❌ Error: API key de OpenAI no configurada. Por favor, verifica tu archivo .env"

        # Construir el historial de conversación para contexto
        historial_contexto = ""
        for chat in conversation_history[-3:]:  # Últimos 3 mensajes
            historial_contexto += f"Usuario: {chat.get('question', '')}\n"
            historial_contexto += f"Asistente: {chat.get('answer', '')}\n\n"

        prompt = f"""
Eres Auditel, un asistente especializado en auditoría con amplio conocimiento en normatividad mexicana.

{contexto}

HISTORIAL RECIENTE:
{historial_contexto}

INSTRUCCIONES ESPECÍFICAS:
- Responde como experto en auditoría basándote en la irregularidad detectada
- Si se detectó una irregularidad específica, enfócate en ella y su normativa aplicable
- Sé preciso y técnico pero claro
- Incluye referencias normativas específicas cuando sea relevante
- Sugiere acciones concretas que un auditor podría tomar
- Proporciona ejemplos de documentación requerida
- Si no se detectó irregularidad específica, responde de forma general pero técnica basándote en el tipo de auditoría
- Mantén un tono profesional pero accesible

PREGUNTA DEL USUARIO: {pregunta}

RESPUESTA:
"""

        # LLAMADA A OPENAI
        if OPENAI_NEW_VERSION:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un auditor experto especializado en normatividad mexicana."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        else:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un auditor experto especializado en normatividad mexicana."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"❌ Error en OpenAI: {e}")
        return f"⚠️ Error al generar respuesta inteligente: {str(e)}"

# === RUTAS PRINCIPALES CORREGIDAS ===

@app.route("/", methods=["GET"])
def index():
    chat_history = get_chat_history()
    return render_template("index.html", chat_history=chat_history)

@app.route("/ask", methods=["POST"])
@requiere_configuracion
def ask():
    """Endpoint principal corregido - ya no requiere tipo_irregularidad"""
    try:
        # Validar y sanitizar entradas
        question = sanitizar_texto(request.form.get("question", ""))
        if not question or len(question) < 3:
            return jsonify({"success": False, "message": "La pregunta debe tener al menos 3 caracteres"})

        auditoria_tipo = validar_auditoria_tipo(request.form.get("auditoria"))
        if not auditoria_tipo:
            return jsonify({"success": False, "message": "Tipo de auditoría inválido"})

        ente_tipo = sanitizar_texto(request.form.get("ente", "No especificado"))

        # DEBUG: Log de los datos recibidos
        logger.info(f"📨 Datos recibidos - Auditoría: {auditoria_tipo}, Ente: {ente_tipo}, Pregunta: {question[:100]}...")

        # DETECCIÓN AUTOMÁTICA DE IRREGULARIDAD
        irregularidad_detectada = detectar_irregularidad_automatica(question, auditoria_tipo, ente_tipo)
        
        # Construir contexto mejorado
        contexto = construir_contexto_mejorado(auditoria_tipo, irregularidad_detectada, question, ente_tipo)

        # Obtener historial de conversación
        chat_history = get_chat_history()

        # Generar respuesta con OpenAI
        answer = generar_respuesta_inteligente(question, contexto, chat_history)

        # Guardar en historial
        nuevo_chat = {
            "question": question,
            "answer": answer,
            "auditoria": auditoria_tipo,
            "irregularidad": irregularidad_detectada.get('tipo', 'No detectada') if irregularidad_detectada else 'No detectada',
            "ente": ente_tipo,
            "timestamp": datetime.now().isoformat()
        }

        chat_history.append(nuevo_chat)

        # Limitar historial a 10 mensajes
        if len(chat_history) > 10:
            chat_history = chat_history[-10:]

        set_chat_history(chat_history)

        logger.info(f"✅ Respuesta generada - Irregularidad detectada: {irregularidad_detectada.get('tipo', 'Ninguna') if irregularidad_detectada else 'Ninguna'}")

        return jsonify({
            "success": True, 
            "answer": answer,
            "irregularidad_detectada": irregularidad_detectada.get('tipo', 'No detectada') if irregularidad_detectada else 'No detectada'
        })

    except Exception as e:
        logger.error(f"❌ Error en /ask: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Error interno del servidor. Por favor, intenta nuevamente."})

@app.route("/sugerir_preguntas", methods=["GET"])
@requiere_configuracion
def sugerir_preguntas():
    """Endpoint simplificado - solo basado en auditoría"""
    try:
        auditoria_tipo = validar_auditoria_tipo(request.args.get('auditoria_tipo'))
        if not auditoria_tipo:
            return jsonify({"success": False, "preguntas": []})

        ente_tipo = sanitizar_texto(request.args.get('ente_tipo', 'No especificado'))

        # Generar preguntas genéricas basadas en el tipo de auditoría
        if auditoria_tipo == "Financiera":
            preguntas = [
                "¿Qué documentación financiera básica debo revisar en una auditoría?",
                "¿Cuáles son los principales indicadores de riesgo financiero?",
                "¿Qué normativa aplica para la presentación de estados financieros?"
            ]
        elif auditoria_tipo == "Obra Pública":
            preguntas = [
                "¿Qué documentación de obra pública es esencial revisar?",
                "¿Cómo verifico el cumplimiento de plazos y presupuestos?",
                "¿Qué normativa rige los contratos de obra pública?"
            ]
        else:
            preguntas = [
                "¿Qué documentación debo revisar en esta auditoría?",
                "¿Cuáles son los principales riesgos a considerar?",
                "¿Qué procedimientos de auditoría recomiendas?"
            ]

        return jsonify({"success": True, "preguntas": preguntas})

    except Exception as e:
        logger.error(f"Error en sugerir_preguntas: {e}")
        return jsonify({"success": False, "preguntas": [
            "¿Qué documentación debo revisar?",
            "¿Cuáles son los principales riesgos?",
            "¿Qué procedimientos recomiendas?"
        ]})

@app.route("/clear", methods=["POST"])
def clear():
    """Limpiar la sesión y comenzar de nuevo"""
    try:
        session.clear()
        flash("🔄 Nueva sesión iniciada.", "success")
        logger.info("✅ Sesión limpiada correctamente")
    except Exception as e:
        logger.error(f"Error al limpiar sesión: {e}")
        flash("⚠️ Error al limpiar la sesión", "error")

    return redirect(url_for("index"))

@app.route("/debug", methods=["GET"])
def debug():
    """Endpoint de depuración"""
    debug_info = {
        "status": "ok",
        "openai_configurado": bool(openai_api_key),
        "bases_cargadas": list(DB_AUDITORIA.keys()),
        "conteo_registros": {k: len(v) for k, v in DB_AUDITORIA.items()},
        "sesion_activa": bool(session.get("chat_history")),
        "mensajes_en_sesion": len(get_chat_history())
    }
    return jsonify(debug_info)

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint de salud para monitoreo"""
    status = {
        "status": "healthy" if openai_api_key and DB_AUDITORIA else "degraded",
        "openai_configured": bool(openai_api_key),
        "databases_loaded": len(DB_AUDITORIA),
        "total_records": sum(len(db) for db in DB_AUDITORIA.values()),
        "timestamp": datetime.now().isoformat()
    }
    return jsonify(status)

# Manejo de errores global
@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "message": "Endpoint no encontrado"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Error 500: {error}")
    return jsonify({"success": False, "message": "Error interno del servidor"}), 500

# === INICIALIZACIÓN ===

if __name__ == "__main__":
    if not openai_api_key:
        logger.error("❌ NO se puede iniciar: OPENAI_API_KEY no configurada")
        exit(1)

    if not DB_AUDITORIA:
        logger.error("❌ NO se puede iniciar: No hay bases de datos cargadas")
        exit(1)

    logger.info("✅ Iniciando Auditel con detección automática de irregularidades")
    logger.info(f"📊 Bases cargadas: {list(DB_AUDITORIA.keys())}")

    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=5020, debug=debug_mode)
