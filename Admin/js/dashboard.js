// CONTROL DE ACCESO: Si no hay sesión activa, redirige inmediatamente al login
if (localStorage.getItem('adminSession') !== 'active') {
    // Usamos ruta relativa limpia para que ngrok no se pierda
    window.location.href = './login_admin.html';
}

// ... (Aquí abajo dejas todo el código de gráficas y lógica que ya tenías en tu dashboard.js) ...
// Variables globales
let usersChart = null;
let conversationChart = null;

// Inicializar dashboard
document.addEventListener('DOMContentLoaded', async () => {
    updateTime();
    setInterval(updateTime, 1000);

    // Cargar datos
    await loadStats();
    await loadCharts();
    await loadRecentActivity();
    await loadAlerts();

    // Actualizar cada 30 segundos
    setInterval(loadStats, 30000);
    setInterval(loadRecentActivity, 30000);
});

// ============ ACTUALIZAR HORA ============
function updateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('es-ES', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
    });
    document.getElementById('current-time').textContent = timeString;
}

// ============ CARGAR ESTADÍSTICAS ============
async function loadStats() {
    const stats = await api.getStats();
    
    if (!stats) {
        showError('No se pudieron cargar las estadísticas');
        return;
    }

    // Actualizar KPIs
    document.getElementById('total-users').textContent = formatNumber(stats.totalUsers);
    document.getElementById('users-change').textContent = `${stats.usersChangeToday > 0 ? '+' : ''}${stats.usersChangeToday}% hoy`;
    
    document.getElementById('total-conversations').textContent = formatNumber(stats.totalConversations);
    document.getElementById('conv-change').textContent = `${stats.conversationsChangeWeek > 0 ? '+' : ''}${stats.conversationsChangeWeek}% esta semana`;
    
    document.getElementById('total-derivations').textContent = formatNumber(stats.totalDerivations);
    document.getElementById('deriv-change').textContent = `${stats.derivationsChangeMonth > 0 ? '+' : ''}${stats.derivationsChangeMonth}% este mes`;
    
    document.getElementById('total-professionals').textContent = formatNumber(stats.totalProfessionals);
    document.getElementById('prof-change').textContent = `${stats.professionalsActive} activos`;

    // Log para debug
    console.log('Stats loaded:', stats);
}

// ============ CARGAR GRÁFICOS ============
async function loadCharts() {
    // Gráfico de usuarios
    const usersData = await api.getUsersChart(7);
    if (usersData) {
        createUsersChart(usersData);
    }

    // Gráfico de conversaciones
    const convData = await api.getConversationChart();
    if (convData) {
        createConversationChart(convData);
    }
}

function createUsersChart(data) {
    const ctx = document.getElementById('usersChart').getContext('2d');
    
    if (usersChart) {
        usersChart.destroy();
    }

    usersChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels || ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'],
            datasets: [{
                label: 'Usuarios nuevos',
                data: data.values || [12, 19, 3, 5, 2, 3, 8],
                borderColor: '#3498DB',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 5,
                pointBackgroundColor: '#3498DB',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: { size: 12 }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function createConversationChart(data) {
    const ctx = document.getElementById('conversationChart').getContext('2d');
    
    if (conversationChart) {
        conversationChart.destroy();
    }

    conversationChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels || ['Primer contacto', 'Seguimiento', 'Cierre'],
            datasets: [{
                data: data.values || [30, 25, 20],
                backgroundColor: [
                    '#5B5EA6',
                    '#1A8917',
                    '#F39C12'
                ],
                borderColor: '#fff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: { size: 12 }
                    }
                }
            }
        }
    });
}

// ============ ACTIVIDAD RECIENTE ============
async function loadRecentActivity() {
    const activity = await api.getRecentActivity(10);
    
    if (!activity || !activity.data) {
        return;
    }

    const tbody = document.getElementById('activity-body');
    tbody.innerHTML = '';

    if (activity.data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #999;">Sin actividad reciente</td></tr>';
        return;
    }

    activity.data.forEach(item => {
        const row = tbody.insertRow();
        row.innerHTML = `
            <td><span class="badge">${getActivityIcon(item.type)}</span></td>
            <td>${truncate(item.userName, 20)}</td>
            <td>${item.action}</td>
            <td>${formatTime(item.timestamp)}</td>
        `;
    });
}

// ============ ALERTAS ============
async function loadAlerts() {
    const alerts = await api.getAlerts();
    
    if (!alerts || !alerts.data) {
        return;
    }

    const container = document.getElementById('alerts-container');
    container.innerHTML = '';

    if (alerts.data.length === 0) {
        container.innerHTML = '<p style="color: #999;">No hay alertas en este momento</p>';
        return;
    }

    alerts.data.forEach(alert => {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${alert.severity}`;
        alertDiv.innerHTML = `
            <span>${alert.icon}</span>
            <div style="flex: 1;">
                <strong>${alert.title}</strong>
                <p>${alert.message}</p>
            </div>
            <button onclick="api.markAlertAsRead(${alert.id})" style="border: none; background: none; cursor: pointer; font-size: 18px;">✕</button>
        `;
        container.appendChild(alertDiv);
    });
}

// ============ UTILIDADES ============

function formatNumber(num) {
    if (!num) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Hace unos segundos';
    if (diffMins < 60) return `Hace ${diffMins} min`;
    if (diffHours < 24) return `Hace ${diffHours} h`;
    if (diffDays < 7) return `Hace ${diffDays} d`;
    
    return date.toLocaleDateString('es-ES');
}

function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

function getActivityIcon(type) {
    const icons = {
        'login': '🔓',
        'logout': '🔒',
        'conversation': '💬',
        'derivation': '🎯',
        'register': '📝',
        'update': '✏️'
    };
    return icons[type] || '📌';
}

function showError(message) {
    console.error(message);
    const container = document.getElementById('alerts-container');
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger';
    alertDiv.innerHTML = `
        <span>⚠️</span>
        <div><strong>Error</strong><p>${message}</p></div>
    `;
    container.insertBefore(alertDiv, container.firstChild);
    setTimeout(() => alertDiv.remove(), 5000);
}