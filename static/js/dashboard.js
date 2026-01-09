/**
 * Sistema de Detección de Fraude - Dashboard
 * Versión 2.0 - Enero 2026
 */
const API_BASE = '';
let refreshInterval = null;

// Usuarios conocidos del sistema
const KNOWN_USERS = [
    { id: 'USR-001', devices: ['DEV-001', 'DEV-PHONE-1'], countries: ['AR'], avgAmount: 15000 },
    { id: 'USR-002', devices: ['DEV-002', 'DEV-PHONE-2'], countries: ['AR', 'BR'], avgAmount: 25000 },
    { id: 'USR-003', devices: ['DEV-003'], countries: ['AR'], avgAmount: 8000 },
    { id: 'USR-004', devices: ['DEV-004', 'DEV-PHONE-4'], countries: ['AR', 'MX', 'CL'], avgAmount: 50000 },
    { id: 'USR-005', devices: ['DEV-PHONE-5'], countries: ['AR'], avgAmount: 12000 }
];

const TRANSACTION_TYPES = ['payment', 'transfer', 'recharge', 'qr'];
const FRAUD_COUNTRIES = ['NG', 'RU', 'CN'];

// Mapeo de alertas a iconos y descripciones
const ALERT_MAP = {
    'high_amount': { icon: '💰', desc: 'Monto inusualmente alto' },
    'velocity': { icon: '⚡', desc: 'Demasiadas transacciones en poco tiempo' },
    'geo_location': { icon: '🌍', desc: 'Cambio de ubicación geográfica sospechoso' },
    'new_device': { icon: '📱', desc: 'Dispositivo no reconocido' },
    'unusual_time': { icon: '🕐', desc: 'Horario inusual de transacción' },
    'first_transaction': { icon: '🆕', desc: 'Primera transacción de cuenta nueva' },
    'dangerous_combination': { icon: '⚠️', desc: 'Combinación crítica de alertas' }
};

document.addEventListener('DOMContentLoaded', () => {
    refreshAll();
    // Auto-refresh cada 3 segundos
    refreshInterval = setInterval(refreshAll, 3000);
});

async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    } catch (e) {
        console.error('API Error:', e);
        return null;
    }
}

// Función principal de refresh - actualiza TODO
async function refreshAll() {
    try {
        const [stats, txs] = await Promise.all([
            apiCall('/api/fraud/stats'),
            apiCall('/api/transactions?limit=20')
        ]);

        if (stats) updateStats(stats);
        if (txs) updateTransactions(txs);
    } catch (e) {
        console.error('Refresh error:', e);
    }
}

function updateStats(stats) {
    const totalEl = document.getElementById('total-transactions');
    const fraudEl = document.getElementById('fraud-count');
    const avgTimeEl = document.getElementById('avg-time');
    const approvedEl = document.getElementById('approved-count');

    if (totalEl) totalEl.textContent = stats.total_transactions || 0;
    if (fraudEl) fraudEl.textContent = stats.fraud_detected || 0;
    if (avgTimeEl) avgTimeEl.innerHTML = `${(stats.avg_processing_time_ms || 0).toFixed(1)}<span class="stat-unit">ms</span>`;
    if (approvedEl) approvedEl.textContent = stats.transactions_by_status?.approved || 0;
}

function updateTransactions(txs) {
    const tbody = document.getElementById('transactions-table');
    if (!tbody) return;

    if (!txs || txs.length === 0) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Sin transacciones. Usá los botones para generar.</td></tr>';
        return;
    }

    tbody.innerHTML = txs.map(tx => {
        const alertsHtml = formatAlerts(tx.fraud_reasons);
        const scoreClass = tx.fraud_score > 0.6 ? 'score-high' : tx.fraud_score > 0.3 ? 'score-medium' : 'score-low';

        return `
            <tr class="tx-row tx-${tx.status}">
                <td class="tx-id">${tx.id.split('-').pop()}</td>
                <td class="tx-user">${tx.user_id}</td>
                <td class="tx-amount">$${formatNumber(tx.amount)}</td>
                <td class="tx-score ${scoreClass}">${(tx.fraud_score * 100).toFixed(0)}%</td>
                <td class="tx-alerts">${alertsHtml}</td>
                <td><span class="status-badge status-${tx.status}">${tx.status === 'approved' ? 'OK' : 'X'}</span></td>
            </tr>
        `;
    }).join('');
}

// Formatear alertas con tooltips individuales
function formatAlerts(reasons) {
    if (!reasons || reasons.length === 0) {
        return '<span class="alert-ok">—</span>';
    }

    const alerts = [];

    for (const reason of reasons) {
        const reasonLower = reason.toLowerCase();
        let matched = null;

        // Buscar coincidencia en el mapa de alertas
        for (const [key, data] of Object.entries(ALERT_MAP)) {
            if (reasonLower.includes(key.replace('_', ' ')) ||
                reasonLower.includes(key) ||
                (key === 'high_amount' && (reasonLower.includes('monto') || reasonLower.includes('amount'))) ||
                (key === 'velocity' && (reasonLower.includes('veloci') || reasonLower.includes('transacciones'))) ||
                (key === 'geo_location' && (reasonLower.includes('país') || reasonLower.includes('country'))) ||
                (key === 'new_device' && (reasonLower.includes('dispositivo') || reasonLower.includes('device'))) ||
                (key === 'unusual_time' && reasonLower.includes('hora')) ||
                (key === 'first_transaction' && (reasonLower.includes('primera') || reasonLower.includes('nueva'))) ||
                (key === 'dangerous_combination' && reasonLower.includes('combinación'))
            ) {
                matched = { ...data, fullReason: reason };
                break;
            }
        }

        if (matched) {
            alerts.push(matched);
        } else {
            alerts.push({ icon: '⚠️', desc: 'Alerta de seguridad', fullReason: reason });
        }
    }

    // Eliminar duplicados por icono
    const unique = [];
    const seen = new Set();
    for (const alert of alerts) {
        if (!seen.has(alert.icon)) {
            seen.add(alert.icon);
            unique.push(alert);
        }
    }

    return unique.map(a =>
        `<span class="alert-icon" title="${a.desc}&#10;${a.fullReason}">${a.icon}</span>`
    ).join('');
}

async function createTransaction(data) {
    try {
        const result = await apiCall('/api/transactions', { method: 'POST', body: JSON.stringify(data) });
        if (!result) {
            showToast('error', 'Error', 'No se pudo crear la transacción');
            return null;
        }

        const isApproved = result.status === 'approved';
        showToast(
            isApproved ? 'success' : 'error',
            isApproved ? 'Aprobada' : 'Rechazada',
            `${data.user_id} | $${formatNumber(data.amount)} | Score: ${(result.fraud_score * 100).toFixed(0)}%`
        );

        // Refresh inmediato
        await refreshAll();
        return result;
    } catch (e) {
        showToast('error', 'Error', 'No se pudo crear la transacción');
        console.error(e);
        return null;
    }
}

// Transacción legítima
function generateLegitTransaction() {
    const user = KNOWN_USERS[Math.floor(Math.random() * KNOWN_USERS.length)];
    const device = user.devices[Math.floor(Math.random() * user.devices.length)];
    const country = user.countries[Math.floor(Math.random() * user.countries.length)];
    const amount = Math.floor(user.avgAmount * (0.3 + Math.random() * 0.7));
    const type = TRANSACTION_TYPES[Math.floor(Math.random() * TRANSACTION_TYPES.length)];

    createTransaction({
        user_id: user.id,
        amount: amount,
        currency: 'ARS',
        transaction_type: type,
        device_id: device,
        ip_address: '190.220.100.' + Math.floor(Math.random() * 255),
        country: country
    });
}

// Transacción fraudulenta
function generateFraudTransaction() {
    const timestamp = Date.now();
    const country = FRAUD_COUNTRIES[Math.floor(Math.random() * FRAUD_COUNTRIES.length)];

    createTransaction({
        user_id: 'USR-NEW-' + timestamp,
        amount: Math.floor(Math.random() * 400000) + 150000,
        currency: 'ARS',
        transaction_type: 'crypto',
        device_id: 'DEV-UNKNOWN-' + Math.floor(Math.random() * 1000),
        ip_address: '123.45.' + Math.floor(Math.random() * 255) + '.' + Math.floor(Math.random() * 255),
        country: country
    });
}

// Batch de transacciones variadas
async function generateBatch() {
    showToast('info', 'Procesando', 'Generando 10 transacciones...');

    const results = { approved: 0, rejected: 0 };

    for (let i = 0; i < 10; i++) {
        const r = Math.random();
        let result;

        if (r < 0.6) {
            // 60% legítimas
            const userIndex = i % KNOWN_USERS.length;
            const user = KNOWN_USERS[userIndex];
            result = await createTransactionSilent({
                user_id: user.id,
                amount: Math.floor(user.avgAmount * (0.3 + Math.random() * 0.7)),
                currency: 'ARS',
                transaction_type: TRANSACTION_TYPES[Math.floor(Math.random() * TRANSACTION_TYPES.length)],
                device_id: user.devices[0],
                ip_address: '190.220.100.' + Math.floor(Math.random() * 255),
                country: user.countries[0]
            });
        } else if (r < 0.85) {
            // 25% sospechosas
            const user = KNOWN_USERS[Math.floor(Math.random() * KNOWN_USERS.length)];
            result = await createTransactionSilent({
                user_id: user.id,
                amount: Math.floor(user.avgAmount * (3 + Math.random() * 3)),
                currency: 'ARS',
                transaction_type: 'transfer',
                device_id: 'DEV-NEW-BATCH-' + i,
                ip_address: '45.67.' + Math.floor(Math.random() * 255) + '.' + Math.floor(Math.random() * 255),
                country: 'BR'
            });
        } else {
            // 15% fraude
            result = await createTransactionSilent({
                user_id: 'USR-BATCH-' + Date.now() + '-' + i,
                amount: Math.floor(Math.random() * 300000) + 200000,
                currency: 'ARS',
                transaction_type: 'crypto',
                device_id: 'DEV-UNKNOWN-' + i,
                ip_address: '123.45.67.' + Math.floor(Math.random() * 255),
                country: FRAUD_COUNTRIES[Math.floor(Math.random() * FRAUD_COUNTRIES.length)]
            });
        }

        if (result) {
            if (result.status === 'approved') results.approved++;
            else results.rejected++;
        }

        await new Promise(res => setTimeout(res, 150));
    }

    await refreshAll();
    showToast('success', 'Completado', `${results.approved} aprobadas, ${results.rejected} rechazadas`);
}

async function createTransactionSilent(data) {
    try {
        return await apiCall('/api/transactions', { method: 'POST', body: JSON.stringify(data) });
    } catch (e) {
        console.error(e);
        return null;
    }
}

// Modal
function openSimulator() {
    document.getElementById('simulator-modal').classList.add('active');
}

function closeSimulator() {
    document.getElementById('simulator-modal').classList.remove('active');
}

async function submitTransaction(e) {
    e.preventDefault();
    await createTransaction({
        user_id: document.getElementById('user_id').value,
        amount: parseFloat(document.getElementById('amount').value),
        currency: 'ARS',
        transaction_type: document.getElementById('transaction_type').value,
        device_id: document.getElementById('device_id').value,
        ip_address: document.getElementById('ip_address').value,
        country: document.getElementById('country').value
    });
    closeSimulator();
}

// Notificaciones toast
function showToast(type, title, msg) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = { success: '✓', error: '✗', info: 'ℹ', warning: '!' };
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || '•'}</span>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${msg}</div>
        </div>
    `;

    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function formatNumber(n) {
    return new Intl.NumberFormat('es-AR').format(n);
}
