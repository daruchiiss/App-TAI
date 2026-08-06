// Admin/js/profesionales.js
import { consumirAPI } from './api.js';

document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Consultar las alertas desde la base de datos
        const data = await consumirAPI('/profesional/alertas?profesional_id=prof_001');
        
        console.log("Alertas recibidas:", data.alertas);
        
        // Ejemplo de renderizado dinámico en el HTML
        const contenedorListado = document.querySelector('.team-list, .alerts-layout');
        if (contenedorListado && data.alertas) {
            contenedorListado.innerHTML = data.alertas.map(alerta => `
                <div class="alert-item" data-id="${alerta.id}">
                    <p><strong>Usuario ID:</strong> ${alerta.usuario_id}</p>
                    <p><strong>Nivel de Severidad:</strong> ${alerta.nivel_severidad}</p>
                    <button class="btn-confirmar" onclick="confirmar(${alerta.id})">Marcar como Atendido</button>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error("Error al cargar alertas en el módulo de profesionales:", error);
    }
});

// Función para confirmar alerta
window.confirmar = async function(alertaId) {
    try {
        await consumirAPI('/profesional/alertas/confirmar', {
            method: 'POST',
            body: JSON.stringify({ alerta_id: alertaId, profesional_id: 'prof_001' })
        });
        alert('Alerta confirmada exitosamente');
        window.location.reload();
    } catch (err) {
        alert('Error al confirmar la alerta');
    }
};