/**
 * TAI - Módulo de Integración: Envío de Reportes a Profesionales
 * Conecta el frontend del paciente con el backend para que los reportes 
 * lleguen al profesional asignado cuando se detecta escalamiento
 */

const TAI_API_CONFIG = {
     BASE_URL: window.location.hostname === "127.0.0.1" 
        ? "http://127.0.0.1:5000" 
        : window.location.origin,
    ENDPOINTS: {
        CHAT: "/chat",
        SEND_REPORT: "/reportes/enviar",
        GET_ALERTS: "/profesional/alertas",
        ACK_ALERT: "/profesional/alertas/confirmar"
    },
    ESCALAMIENTO_NIVELES: {
        1: "TRANQUILO",
        2: "ATENCION", 
        3: "CRISIS"
    }
};

/**
 * Clase principal para manejar la integración de reportes
 */
class TAIReporteManager {
    constructor(usuarioId, profesionalId = null) {
        this.usuarioId = usuarioId;
        this.profesionalId = profesionalId;
        this.nivelActual = 1;
        this.sesionActiva = true;
        this.reporteEnviado = false;
        this.pollInterval = null;
    }

    /**
     * Envía un mensaje al chat y maneja el escalamiento
     * @param {string} mensaje - Mensaje del usuario
     * @returns {Promise} Respuesta del backend
     */
    async enviarMensajeChat(mensaje) {
        try {
            const respuesta = await fetch(
                `${TAI_API_CONFIG.BASE_URL}${TAI_API_CONFIG.ENDPOINTS.CHAT}`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'ngrok-skip-browser-warning': 'true'
                    },
                    body: JSON.stringify({
                        mensaje: mensaje,
                        usuario_id: parseInt(this.usuarioId)
                    })
                }
            );

            const datos = await respuesta.json();

            if (respuesta.ok && datos.texto_respuesta) {
                // Verificar si hay escalamiento
                if (datos.escalamiento_activado && datos.nivel_escalamiento) {
                    await this.manejarEscalamiento(datos);
                }
                return datos;
            } else {
                throw new Error("Error en respuesta del chat");
            }
        } catch (error) {
            console.error("Error enviando mensaje:", error);
            throw error;
        }
    }

    /**
     * Maneja el escalamiento y envía reporte al profesional
     * @param {object} datosChat - Datos de respuesta del chat
     */
    async manejarEscalamiento(datosChat) {
        const nivelEscalamiento = datosChat.nivel_escalamiento || 1;
        
        // Actualizar nivel actual
        this.nivelActual = Math.max(this.nivelActual, nivelEscalamiento);

        // Si es crisis (nivel 3), enviar reporte inmediatamente
        if (nivelEscalamiento === 3 && !this.reporteEnviado) {
            await this.enviarReporteProfesional(datosChat);
        }
    }

    /**
     * Construye el reporte con toda la información de la sesión
     * @param {object} datosChat - Datos del último mensaje
     * @returns {object} Reporte formateado
     */
    construirReporte(datosChat) {
        return {
            usuario_id: parseInt(this.usuarioId),
            tipo_alerta: TAI_API_CONFIG.ESCALAMIENTO_NIVELES[this.nivelActual] || "CRISIS",
            nivel_severidad: this.nivelActual,
            timestamp: new Date().toISOString(),
            datos_clinicos: {
                score_crisis: datosChat.score_crisis || null,
                triggers_detectados: datosChat.triggers_detectados || [],
                cambios_de_comportamiento: datosChat.cambios_de_comportamiento || null
            },
            resumen_ia: datosChat.resumen_ia || null,
            contacto_emergencia: datosChat.contacto_emergencia || null,
            historial_escalamientos: datosChat.historial_escalamientos || [],
            recomendaciones: datosChat.recomendaciones || []
        };
    }

    /**
     * Envía el reporte al profesional asignado
     * @param {object} datosChat - Datos del chat
     * @returns {Promise} Respuesta del envío
     */
    async enviarReporteProfesional(datosChat) {
        try {
            const reporte = this.construirReporte(datosChat);

            const respuesta = await fetch(
                `${TAI_API_CONFIG.BASE_URL}${TAI_API_CONFIG.ENDPOINTS.SEND_REPORT}`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'ngrok-skip-browser-warning': 'true'
                    },
                    body: JSON.stringify(reporte)
                }
            );

            const resultado = await respuesta.json();

            if (respuesta.ok) {
                this.reporteEnviado = true;
                console.log("✓ Reporte enviado al profesional:", resultado);
                return resultado;
            } else {
                throw new Error(resultado.error || "Error al enviar reporte");
            }
        } catch (error) {
            console.error("✗ Error enviando reporte al profesional:", error);
            throw error;
        }
    }

    /**
     * Inicia polling para que el profesional reciba alertas en tiempo real
     * Solo debe llamarse desde el dashboard del profesional
     * @param {function} callback - Función a ejecutar cuando hay nuevas alertas
     * @param {number} intervalo - Millisegundos entre polls (default: 5000)
     */
    iniciarPollAlertas(callback, intervalo = 5000) {
        if (this.pollInterval) clearInterval(this.pollInterval);

        this.pollInterval = setInterval(async () => {
            try {
                const alertas = await this.obtenerAlertas();
                if (alertas && alertas.length > 0) {
                    callback(alertas);
                }
            } catch (error) {
                console.error("Error obteniendo alertas:", error);
            }
        }, intervalo);

        return this.pollInterval;
    }

    /**
     * Obtiene las alertas pendientes para el profesional
     * @returns {Promise<array>} Lista de alertas
     */
    async obtenerAlertas() {
        try {
            const respuesta = await fetch(
                `${TAI_API_CONFIG.BASE_URL}${TAI_API_CONFIG.ENDPOINTS.GET_ALERTS}?profesional_id=${this.profesionalId}`,
                {
                    method: 'GET',
                    headers: {
                        'ngrok-skip-browser-warning': 'true'
                    }
                }
            );

            if (respuesta.ok) {
                const datos = await respuesta.json();
                return datos.alertas || [];
            }
            return [];
        } catch (error) {
            console.error("Error obteniendo alertas:", error);
            return [];
        }
    }

    /**
     * Confirma que el profesional ha visto/procesado una alerta
     * @param {string} alertaId - ID de la alerta
     * @returns {Promise} Respuesta del servidor
     */
    async confirmarAlerta(alertaId) {
        try {
            const respuesta = await fetch(
                `${TAI_API_CONFIG.BASE_URL}${TAI_API_CONFIG.ENDPOINTS.ACK_ALERT}`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'ngrok-skip-browser-warning': 'true'
                    },
                    body: JSON.stringify({
                        alerta_id: alertaId,
                        profesional_id: this.profesionalId,
                        timestamp_confirmacion: new Date().toISOString()
                    })
                }
            );

            return await respuesta.json();
        } catch (error) {
            console.error("Error confirmando alerta:", error);
            throw error;
        }
    }

    /**
     * Detiene el polling de alertas
     */
    detenerPollAlertas() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    /**
     * Limpia recursos cuando termina la sesión
     */
    finalizarSesion() {
        this.sesionActiva = false;
        this.detenerPollAlertas();
    }
}

/**
 * Interfaz para el flujo del USUARIO (Paciente)
 * Se usa en chatbot.html
 */
class TAIUserFlow {
    constructor() {
        this.usuarioId = localStorage.getItem("usuario_id") || "1";
        this.reportManager = new TAIReporteManager(this.usuarioId);
    }

    async enviarMensaje(mensaje) {
        return await this.reportManager.enviarMensajeChat(mensaje);
    }

    finalizar() {
        this.reportManager.finalizarSesion();
    }
}

/**
 * Interfaz para el flujo del PROFESIONAL (Doctor)
 * Se usa en dashboard_profesional.html
 */
class TAIProfesionalFlow {
    constructor(profesionalId) {
        this.profesionalId = profesionalId;
        this.reportManager = new TAIReporteManager(null, profesionalId);
        this.alertasActivas = [];
    }

    /**
     * Inicia el monitoreo de alertas en tiempo real
     * @param {function} onNuevaAlerta - Callback cuando llega nueva alerta
     */
    iniciarMonitoreo(onNuevaAlerta) {
        return this.reportManager.iniciarPollAlertas((alertas) => {
            this.alertasActivas = alertas;
            onNuevaAlerta(alertas);
        });
    }

    /**
     * Procesa una alerta (marcar como vista, aceptar, etc.)
     * @param {string} alertaId - ID de la alerta
     * @param {string} accion - 'acepta', 'rechaza', 'escalada'
     */
    async procesarAlerta(alertaId, accion) {
        const alerta = this.alertasActivas.find(a => a.id === alertaId);
        if (!alerta) return null;

        try {
            const resultado = await this.reportManager.confirmarAlerta(alertaId);
            alerta.estado = accion;
            alerta.timestamp_procesamiento = new Date().toISOString();
            return resultado;
        } catch (error) {
            console.error("Error procesando alerta:", error);
            throw error;
        }
    }

    /**
     * Acepta un caso de paciente en crisis
     * @param {string} usuarioId - ID del paciente
     */
    async aceptarCanalizacion(usuarioId) {
        return this.procesarAlerta(usuarioId, "aceptada");
    }

    detener() {
        this.reportManager.detenerPollAlertas();
    }
}

// Exportar para uso en navegador
if (typeof window !== 'undefined') {
    window.TAI_CONFIG = TAI_API_CONFIG;
    window.TAIReporteManager = TAIReporteManager;
    window.TAIUserFlow = TAIUserFlow;
    window.TAIProfesionalFlow = TAIProfesionalFlow;
}