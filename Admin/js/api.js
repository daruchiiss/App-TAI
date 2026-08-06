// Admin/js/api.js
const API_BASE_URL = "http://127.0.0.1:5000";

export async function consumirAPI(endpoint, opciones = {}) {
    const configuracion = {
        headers: {
            'Content-Type': 'application/json',
            ...opciones.headers
        },
        ...opciones
    };

    try {
        const respuesta = await fetch(`${API_BASE_URL}${endpoint}`, configuracion);
        if (!respuesta.ok) {
            throw new Error(`Error HTTP: ${respuesta.status}`);
        }
        return await respuesta.json();
    } catch (error) {
        console.error(`Error al solicitar ${endpoint}:`, error);
        throw error;
    }
}