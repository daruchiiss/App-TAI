import { fetchAPI } from './api.js';

document.addEventListener('DOMContentLoaded', cargarUsuarios);

async function cargarUsuarios() {
    try {
        const usuarios = await fetchAPI('/api/usuarios');
        const tabla = document.querySelector('#tabla-usuarios tbody'); // Usa el ID de tu <tbody>
        
        tabla.innerHTML = usuarios.map(usr => `
            <tr>
                <td>${usr.id}</td>
                <td>${usr.nombre}</td>
                <td>${usr.email}</td>
                <td><span class="badge ${usr.estado}">${usr.estado}</span></td>
            </tr>
        `).join('');
    } catch (err) {
        alert("No se pudieron cargar los usuarios");
    }
}