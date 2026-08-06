import json
import sqlite3
from datetime import datetime
import bcrypt

DB_NAME = "tai.db"

def inicializar_db():
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()

    # Tabla usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            edad INTEGER NOT NULL,
            es_menor BOOLEAN,
            tutor_nombre TEXT,
            tutor_contacto TEXT,
            contacto_emergencia_nombre TEXT,
            contacto_emergencia_telefono TEXT,
            consentimiento_aceptado BOOLEAN,
            fecha_registro TEXT
        )
    """)

    # Tabla interacciones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            mensaje_usuario TEXT,
            respuesta_ia TEXT,
            nivel TEXT,
            justificacion TEXT,
            requiere_escalamiento BOOLEAN,
            escalamiento_activado BOOLEAN,
            fecha_hora TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    """)

    # Tabla alertas_criticas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alertas_criticas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            profesional_id TEXT,
            tipo_alerta TEXT,
            nivel_severidad INTEGER,
            datos_clinicos TEXT,
            resumen_ia TEXT,
            contacto_emergencia TEXT,
            historial_escalamientos TEXT,
            recomendaciones TEXT,
            estado TEXT DEFAULT 'pendiente',
            timestamp_alerta TEXT NOT NULL,
            timestamp_confirmacion TEXT,
            timestamp_procesamiento TEXT,
            created_at TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    """)

    conexion.commit()
    conexion.close()

def registrar_usuario(nombre, email, password_plana, edad, tutor_nombre=None, tutor_contacto=None,
                      contacto_emergencia_nombre=None, contacto_emergencia_telefono=None,
                      consentimiento_aceptado=False):
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()

    es_menor = edad < 18
    password_encriptada = bcrypt.hashpw(password_plana.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        cursor.execute("""
            INSERT INTO usuarios 
            (nombre, email, password, edad, es_menor, tutor_nombre, tutor_contacto, 
             contacto_emergencia_nombre, contacto_emergencia_telefono, 
             consentimiento_aceptado, fecha_registro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nombre, email, password_encriptada, edad, es_menor, tutor_nombre, tutor_contacto,
            contacto_emergencia_nombre, contacto_emergencia_telefono,
            consentimiento_aceptado, datetime.now().isoformat()
        ))
        usuario_id = cursor.lastrowid
        conexion.commit()
    except sqlite3.IntegrityError:
        usuario_id = None  # El email ya existe
    finally:
        conexion.close()
        
    return usuario_id

def verificar_credenciales(email, password_plana):
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    
    cursor.execute("SELECT id, password FROM usuarios WHERE email = ?", (email,))
    resultado = cursor.fetchone()
    conexion.close()
    
    if resultado:
        usuario_id, password_encriptada = resultado
        if bcrypt.checkpw(password_plana.encode('utf-8'), password_encriptada.encode('utf-8')):
            return usuario_id
            
    return None

def obtener_usuario(usuario_id):
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
    resultado = cursor.fetchone()
    conexion.close()
    return resultado

def guardar_interaccion(usuario_id, mensaje_usuario, respuesta_ia, clasificacion, escalamiento_activado):
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()

    nivel = clasificacion.get("nivel") if clasificacion else None
    justificacion = clasificacion.get("justificacion") if clasificacion else None
    requiere_escalamiento = clasificacion.get("requiere_escalamiento") if clasificacion else False

    cursor.execute("""
        INSERT INTO interacciones 
        (usuario_id, mensaje_usuario, respuesta_ia, nivel, justificacion, requiere_escalamiento, escalamiento_activado, fecha_hora)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        usuario_id, mensaje_usuario, respuesta_ia, nivel, justificacion,
        requiere_escalamiento, escalamiento_activado, datetime.now().isoformat()
    ))

    conexion.commit()
    conexion.close()

def obtener_historial_usuario(usuario_id):
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT mensaje_usuario, respuesta_ia, nivel, fecha_hora 
        FROM interacciones 
        WHERE usuario_id = ?
        ORDER BY fecha_hora ASC
    """, (usuario_id,))

    resultados = cursor.fetchall()
    conexion.close()
    return resultados

# ════════════════════════════════════════════════════════════════
# FUNCIONES DE ALERTAS CRÍTICAS
# ════════════════════════════════════════════════════════════════

def guardar_alerta_critica(usuario_id, tipo_alerta, nivel_severidad, datos_clinicos, 
                          resumen_ia, contacto_emergencia, historial_escalamientos, 
                          recomendaciones, profesional_id="prof_001"):
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO alertas_criticas 
            (usuario_id, profesional_id, tipo_alerta, nivel_severidad, 
             datos_clinicos, resumen_ia, contacto_emergencia, 
             historial_escalamientos, recomendaciones, 
             estado, timestamp_alerta, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            usuario_id,
            profesional_id,
            tipo_alerta,
            nivel_severidad,
            json.dumps(datos_clinicos) if isinstance(datos_clinicos, (dict, list)) else datos_clinicos,
            resumen_ia,
            contacto_emergencia,
            json.dumps(historial_escalamientos) if isinstance(historial_escalamientos, list) else historial_escalamientos,
            json.dumps(recomendaciones) if isinstance(recomendaciones, list) else recomendaciones,
            'pendiente',
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        alerta_id = cursor.lastrowid
        conexion.commit()
        print(f"✓ Alerta crítica guardada con éxito en la BD. ID: {alerta_id}")
        return alerta_id
        
    except Exception as e:
        print(f"✗ Error guardando alerta crítica en la BD: {e}")
        return None
    finally:
        conexion.close()


def obtener_alertas_pendientes(profesional_id="prof_001"):
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                id, usuario_id, tipo_alerta, nivel_severidad, 
                datos_clinicos, resumen_ia, contacto_emergencia, 
                historial_escalamientos, recomendaciones, estado, timestamp_alerta
            FROM alertas_criticas
            WHERE estado = 'pendiente'
            ORDER BY timestamp_alerta DESC
        """)
        
        resultados = cursor.fetchall()
        
        alertas = []
        for fila in resultados:
            # 💡 Mantiene el ID numérico limpio para evitar prefijos dobles USR-
            raw_usr = str(fila[1])
            usr_clean = raw_usr if raw_usr.startswith("USR-") else f"USR-{raw_usr}"

            alerta = {
                "id": fila[0],  # ID primario numérico de la alerta
                "usuario_id": usr_clean,
                "tipo_alerta": fila[2],
                "nivel_severidad": fila[3],
                "datos_clinicos": json.loads(fila[4]) if fila[4] and isinstance(fila[4], str) else fila[4],
                "resumen_ia": fila[5],
                "contacto_emergencia": fila[6],
                "historial_escalamientos": json.loads(fila[7]) if fila[7] and isinstance(fila[7], str) else fila[7],
                "recomendaciones": json.loads(fila[8]) if fila[8] and isinstance(fila[8], str) else fila[8],
                "estado": fila[9],
                "timestamp": fila[10]
            }
            alertas.append(alerta)
        
        return alertas
        
    except Exception as e:
        print(f"✗ Error obteniendo alertas: {e}")
        return []
    finally:
        conexion.close()


def confirmar_alerta(alerta_id, profesional_id="prof_001", nuevo_estado="en_proceso"):
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    
    try:
        # 🧹 Extrae únicamente el número del ID (por si el frontend envía "USR-1" o "1")
        if isinstance(alerta_id, str):
            alerta_id_limpio = int(''.join(filter(str.isdigit, alerta_id)))
        else:
            alerta_id_limpio = int(alerta_id)

        # Actualiza la alerta en SQLite independientemente del string del profesional
        cursor.execute("""
            UPDATE alertas_criticas
            SET estado = ?, 
                timestamp_confirmacion = ?,
                timestamp_procesamiento = ?
            WHERE id = ?
        """, (
            nuevo_estado,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            alerta_id_limpio
        ))
        
        conexion.commit()
        
        if cursor.rowcount > 0:
            print(f"✓ Éxito: Alerta #{alerta_id_limpio} actualizada correctamente en `tai.db` a estado '{nuevo_estado}'")
            return True
        else:
            print(f"✗ Error: No se encontró la alerta #{alerta_id_limpio} en la tabla 'alertas_criticas'")
            return False
            
    except Exception as e:
        print(f"✗ Error en la consulta SQL de confirmación: {e}")
        return False
    finally:
        conexion.close()

def obtener_alerta_por_id(alerta_id):
    """
    Obtiene los detalles de una alerta individual según su ID.
    """
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    
    try:
        # Extrae solo el número si el frontend envía formatos como "USR-1" o "1"
        if isinstance(alerta_id, str):
            alerta_id_limpio = int(''.join(filter(str.isdigit, alerta_id)))
        else:
            alerta_id_limpio = int(alerta_id)

        cursor.execute("""
            SELECT id, usuario_id, tipo_alerta, nivel_severidad, datos_clinicos, 
                   resumen_ia, contacto_emergencia, historial_escalamientos, 
                   recomendaciones, profesional_id, estado, timestamp_alerta
            FROM alertas_criticas
            WHERE id = ?
        """, (alerta_id_limpio,))
        
        alerta = cursor.fetchone()
        
        if alerta:
            raw_usr = str(alerta[1])
            usr_clean = raw_usr if raw_usr.startswith("USR-") else f"USR-{raw_usr}"

            return {
                "id": alerta[0],
                "usuario_id": usr_clean,
                "tipo_alerta": alerta[2],
                "nivel_severidad": alerta[3],
                "datos_clinicos": json.loads(alerta[4]) if alerta[4] and isinstance(alerta[4], str) else (alerta[4] or {}),
                "resumen_ia": alerta[5],
                "contacto_emergencia": alerta[6],
                "historial_escalamientos": json.loads(alerta[7]) if alerta[7] and isinstance(alerta[7], str) else (alerta[7] or []),
                "recomendaciones": json.loads(alerta[8]) if alerta[8] and isinstance(alerta[8], str) else (alerta[8] or []),
                "profesional_id": alerta[9],
                "estado": alerta[10],
                "timestamp": alerta[11]
            }
        return None
    except Exception as e:
        print(f"✗ Error obteniendo alerta por ID ({alerta_id}): {e}")
        return None
    finally:
        conexion.close()

if __name__ == "__main__":
    inicializar_db()
    print("Base de datos TAI inicializada y lista.")