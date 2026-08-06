from flask import Flask, request, jsonify, render_template
from database import (
    inicializar_db, guardar_interaccion, registrar_usuario, obtener_usuario, 
    verificar_credenciales, guardar_alerta_critica, obtener_alertas_pendientes, confirmar_alerta
)
from datetime import datetime
from flask_cors import CORS
import os

# ⚠️ IMPORTANTE: Ajusta 'tu_modulo_ia' por el nombre real del archivo .py donde está analizar_mensaje
# Ejemplo: si está en ia.py -> from ia import analizar_mensaje
try:
    from chatbot import analizar_mensaje
except ImportError:
    # Función de respaldo (fallback) por si el archivo de IA tiene otro nombre
    def analizar_mensaje(historial):
        return {
            "texto_respuesta": "Hola, estoy procesando tu mensaje correctamente.",
            "clasificacion": {"nivel": "Tranquilo", "requiere_escalamiento": False}
        }

# Le indicamos a Flask que busque templates en la carpeta Frontend o templates del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(os.path.dirname(BASE_DIR), "Frontend")

app = Flask(__name__,)

# 🌐 Configuración global de CORS sin restricciones
CORS(app, supports_credentials=True)

# Inicializamos la base de datos al arrancar
try:
    inicializar_db()
    print("✅ Base de datos inicializada correctamente.")
except Exception as e:
    print(f"⚠️ Error al inicializar la base de datos: {e}")

# Historial indexado por usuario_id
historiales_usuarios = {}

# ═══════════════════════════════════════════════════════════════
# 🌐 VISTAS DE PÁGINAS WEB (Frontend)
# ═══════════════════════════════════════════════════════════════

@app.route("/")
def inicio():
    """Ruta principal que entrega la interfaz del chat"""
    return render_template("chatbot.html")


# ═══════════════════════════════════════════════════════════════
# 📩 RUTAS DE LA API
# ═══════════════════════════════════════════════════════════════

@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    """Procesar mensaje de chat"""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    print("\n [POST /chat] Nueva petición recibida...")
    
    datos = request.get_json(silent=True)
    if not datos or not isinstance(datos, dict):
        print(" Error: Datos recibidos no válidos o vacíos.")
        return jsonify({"error": "Formato de datos inválido"}), 400

    mensaje_usuario = datos.get("mensaje", "")
    usuario_id = datos.get("usuario_id", 1)

    if not mensaje_usuario:
        print(" Error: El campo 'mensaje' vino vacío.")
        return jsonify({"error": "No se recibió ningún mensaje"}), 400

    print(f" Usuario (ID: {usuario_id}): {mensaje_usuario}")

    # Obtener o crear historial propio del usuario
    if usuario_id not in historiales_usuarios:
        historiales_usuarios[usuario_id] = []
    
    historial_usuario = historiales_usuarios[usuario_id]
    historial_usuario.append({"role": "user", "content": mensaje_usuario})

    # --- 1. PROCESAR MENSAJE CON LA IA ---
    try:
        print(" Consultando a la IA (analizar_mensaje)...")
        resultado = analizar_mensaje(historial_usuario)
        print(" Respuesta recibida de la IA.")
    except Exception as e:
        print(f" ERROR CRÍTICO dentro de analizar_mensaje(): {e}")
        return jsonify({
            "texto_respuesta": "Lo siento, tuve un problema interno al procesar tu respuesta con el modelo de IA.",
            "error": str(e)
        }), 500

    # Extraer respuesta
    texto_respuesta = resultado.get("texto_respuesta", "No pude generar una respuesta.")
    if texto_respuesta:
        historial_usuario.append({"role": "assistant", "content": texto_respuesta})

    # --- 2. ESCALAMIENTO ---
    escalamiento_activado = False
    clasificacion = resultado.get("clasificacion") or {}
    
    if clasificacion and clasificacion.get("requiere_escalamiento"):
        escalamiento_activado = True
        print(" ESCALAMIENTO ACTIVADO — Se simula notificación a orientador de Nivel 2 🚨")

    resultado["escalamiento_activado"] = escalamiento_activado

    # --- 3. GUARDAR EN BASE DE DATOS ---
    try:
        guardar_interaccion(
            usuario_id, 
            mensaje_usuario, 
            texto_respuesta,
            clasificacion, 
            escalamiento_activado
        )
        print(" Interacción guardada en la base de datos.")
    except Exception as e:
        print(f" Advertencia: No se pudo guardar la interacción en DB: {e}")

    print(" Respondiendo al cliente exitosamente (200 OK).\n")
    return jsonify(resultado), 200


# ═══════════════════════════════════════════════════════════════
# 🔐 RUTAS DE AUTENTICACIÓN
# ═══════════════════════════════════════════════════════════════

@app.route("/registro", methods=["POST"])
def registro():
    """Registrar nuevo usuario"""
    datos = request.get_json(silent=True)
    if not datos or not isinstance(datos, dict):
        return jsonify({"error": "Formato de datos inválido"}), 400

    nombre = datos.get("nombre", "")
    email = datos.get("email", "")
    password = datos.get("password", "")
    edad = datos.get("edad")
    consentimiento_aceptado = datos.get("consentimiento_aceptado", False)

    if not nombre or edad is None or not email or not password:
        return jsonify({"error": "Nombre, edad, correo y contraseña son obligatorios"}), 400

    if not consentimiento_aceptado:
        return jsonify({"error": "Debes aceptar el consentimiento informado para registrarte"}), 400

    usuario_id = registrar_usuario(
        nombre=nombre,
        email=email,
        password_plana=password,
        edad=edad,
        tutor_nombre=datos.get("tutor_nombre"),
        tutor_contacto=datos.get("tutor_contacto"),
        contacto_emergencia_nombre=datos.get("contacto_emergencia_nombre"),
        contacto_emergencia_telefono=datos.get("contacto_emergencia_telefono"),
        consentimiento_aceptado=consentimiento_aceptado
    )

    if usuario_id is None:
        return jsonify({"error": "El correo electrónico ya se encuentra registrado"}), 400

    return jsonify({"usuario_id": usuario_id, "mensaje": "Registro exitoso"}), 201


@app.route("/login", methods=["POST"])
def login():
    datos = request.get_json()
    email = datos.get("email")
    password = datos.get("password")
    rol = datos.get("rol")

    # Aquí haces la validación de tu base de datos o lógica de usuario
    if email and password:
        return jsonify({
            "exito": True,
            "usuario_id": "usr_12345",
            "mensaje": "Inicio de sesión correcto"
        }), 200
    else:
        return jsonify({
            "exito": False,
            "mensaje": "Credenciales inválidas"
        }), 400

@app.route("/reiniciar", methods=["POST"])
def reiniciar():
    """Reiniciar el historial de conversación"""
    datos = request.get_json(silent=True) or {}
    usuario_id = datos.get("usuario_id")
    
    if usuario_id and usuario_id in historiales_usuarios:
        historiales_usuarios[usuario_id].clear()
    else:
        historiales_usuarios.clear()

    return jsonify({"mensaje": "Historial reiniciado"}), 200


# ═══════════════════════════════════════════════════════════════
# 📨 ENDPOINT: Enviar reporte de crisis al profesional
# ═══════════════════════════════════════════════════════════════

@app.route("/reportes/enviar", methods=["POST", "OPTIONS"])
def enviar_reporte():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:
        print("\n [POST /reportes/enviar] Reporte de crisis recibido...")
        datos = request.get_json(silent=True)
        if not datos or not isinstance(datos, dict):
            return jsonify({'error': 'Formato de datos inválido', 'reporte_guardado': False}), 400
        
        usuario_id = datos.get('usuario_id')
        tipo_alerta = datos.get('tipo_alerta', 'CRISIS')
        nivel_severidad = datos.get('nivel_severidad', 3)
        
        if not usuario_id:
            return jsonify({'error': 'usuario_id es obligatorio', 'reporte_guardado': False}), 400
        
        profesional_id = datos.get('profesional_id', 'prof_001')
        
        alerta_id = guardar_alerta_critica(
            usuario_id=usuario_id,
            tipo_alerta=tipo_alerta,
            nivel_severidad=nivel_severidad,
            datos_clinicos=datos.get('datos_clinicos', {}),
            resumen_ia=datos.get('resumen_ia', ''),
            contacto_emergencia=datos.get('contacto_emergencia', ''),
            historial_escalamientos=datos.get('historial_escalamientos', []),
            recomendaciones=datos.get('recomendaciones', []),
            profesional_id=profesional_id
        )
        
        if alerta_id:
            return jsonify({
                'exito': True,
                'alerta_id': alerta_id,
                'profesional_notificado': profesional_id,
                'timestamp_procesamiento': datetime.now().isoformat()
            }), 201
        else:
            return jsonify({'error': 'Error al guardar el reporte', 'reporte_guardado': False}), 500
            
    except Exception as e:
        return jsonify({'error': str(e), 'reporte_guardado': False}), 500


# ═══════════════════════════════════════════════════════════════
# 📋 ENDPOINT: Obtener alertas pendientes del profesional
# ═══════════════════════════════════════════════════════════════

@app.route("/profesional/alertas", methods=["GET"])
def obtener_alertas():
    try:
        profesional_id = request.args.get('profesional_id', 'prof_001')
        if not profesional_id:
            return jsonify({'error': 'Falta profesional_id', 'alertas': []}), 400
        
        alertas = obtener_alertas_pendientes(profesional_id)
        return jsonify({'alertas': alertas, 'cantidad': len(alertas), 'timestamp': datetime.now().isoformat()}), 200
    except Exception as e:
        return jsonify({'error': str(e), 'alertas': []}), 500


# ═══════════════════════════════════════════════════════════════
# ✅ ENDPOINT: Confirmar alerta
# ═══════════════════════════════════════════════════════════════

@app.route("/profesional/alertas/confirmar", methods=["POST", "OPTIONS"])
def confirmar_alerta_endpoint():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:
        datos = request.get_json(silent=True)
        if not datos or not isinstance(datos, dict):
            return jsonify({'error': 'Formato de datos inválido'}), 400
        
        alerta_id = datos.get('alerta_id')
        profesional_id = datos.get('profesional_id', 'prof_001')
        nuevo_estado = datos.get('nuevo_estado', 'confirmada')
        
        if not alerta_id:
            return jsonify({'error': 'alerta_id es obligatorio'}), 400
        
        exito = confirmar_alerta(alerta_id, profesional_id, nuevo_estado)
        if exito:
            return jsonify({'exito': True, 'mensaje': f'Alerta {nuevo_estado}', 'alerta_id': alerta_id}), 200
        else:
            return jsonify({'exito': False, 'error': 'No se pudo confirmar'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# 📊 RUTAS ADMIN
# ═══════════════════════════════════════════════════════════════

@app.route("/admin/usuarios", methods=["GET"])
def admin_obtener_usuarios():
    return jsonify({"exito": True, "usuarios": []}), 200

@app.route("/admin/dashboard/metricas", methods=["GET"])
def admin_obtener_metricas():
    return jsonify({"total_usuarios": 150, "alertas_criticas": 5, "interacciones_hoy": 42}), 200

@app.route("/reset", methods=["GET", "POST"])
def reset_chat():
    global historial_conversacion
    historial_conversacion.clear()
    print("\n🧹 [RESET] Historial de chat vaciado con éxito.")
    return jsonify({"status": "ok", "message": "Historial borrado"}), 200

if __name__ == "__main__":
    # Escucha en todas las interfaces en el puerto 5000
    app.run(host="0.0.0.0", port=5000, debug=True)